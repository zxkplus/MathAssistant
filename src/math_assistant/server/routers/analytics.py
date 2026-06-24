"""Analytics router: mastery, trends, weaknesses, recommendations, and summary."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from math_assistant.server.database import get_db
from math_assistant.server.dependencies import get_current_user
from math_assistant.server.models.answer_record import AnswerRecord
from math_assistant.server.models.knowledge_point import KnowledgePoint
from math_assistant.server.models.learning_session import LearningSession
from math_assistant.server.models.mastery import MasteryScore
from math_assistant.server.models.question import Question
from math_assistant.server.models.question_tag import QuestionTag
from math_assistant.server.models.user import User
from math_assistant.server.schemas.analytics import (
    MasteryDetailResponse,
    MasteryHistoryPoint,
    MasteryItemResponse,
    MasteryListResponse,
    MistakeNotebookItem,
    MistakeNotebookResponse,
    RecommendationItemResponse,
    RecommendationListResponse,
    SuggestedAction,
    SummaryResponse,
    TrendPeriodItem,
    TrendResponse,
    WeaknessItemResponse,
    WeaknessListResponse,
)
from math_assistant.server.services.analytics_engine import (
    compute_mastery_trend,
    get_recommendations,
    get_weaknesses,
)

router = APIRouter()


@router.get("/mastery", response_model=MasteryListResponse)
def get_mastery(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get mastery scores for all knowledge points the user has attempted."""
    records = (
        db.query(MasteryScore)
        .filter(MasteryScore.user_id == current_user.id)
        .all()
    )

    items = []
    total_score = 0
    for m in records:
        kp = db.query(KnowledgePoint).filter(KnowledgePoint.id == m.knowledge_point_id).first()
        if not kp:
            continue

        trend = compute_mastery_trend(current_user.id, m.knowledge_point_id, db)

        items.append(
            MasteryItemResponse(
                knowledge_point_id=m.knowledge_point_id,
                knowledge_point_name=kp.name,
                full_path=kp.full_path,
                score=round(m.score, 1),
                confidence=round(m.confidence, 2),
                total_attempts=m.total_attempts,
                correct_attempts=m.correct_attempts,
                streak=m.streak,
                last_attempted_at=m.last_attempted_at,
                trend=trend,
            )
        )
        total_score += m.score * m.confidence  # Weight by confidence

    # Overall score: weighted average
    total_confidence = sum(m.confidence for m in records)
    overall = round(total_score / max(total_confidence, 1), 1)

    return MasteryListResponse(items=items, overall_score=overall)


@router.get("/mastery/{kp_id}", response_model=MasteryDetailResponse)
def get_mastery_detail(
    kp_id: int,
    period: str = Query("30d", description="Time period: 7d, 30d, 90d, all"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get detailed mastery history for a specific knowledge point."""
    kp = db.query(KnowledgePoint).filter(KnowledgePoint.id == kp_id).first()
    if not kp:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge point not found")

    mastery = (
        db.query(MasteryScore)
        .filter(
            MasteryScore.user_id == current_user.id,
            MasteryScore.knowledge_point_id == kp_id,
        )
        .first()
    )

    current_score = mastery.score if mastery else 0.0

    # Build history from answer records
    days = {"7d": 7, "30d": 30, "90d": 90}.get(period, None)
    query = db.query(AnswerRecord).filter(
        AnswerRecord.user_id == current_user.id,
        AnswerRecord.knowledge_point_id == kp_id,
    )
    if days:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        query = query.filter(AnswerRecord.created_at >= since)

    records = query.order_by(AnswerRecord.created_at.asc()).all()

    # Group by date for history
    date_scores: dict[str, dict] = {}
    for r in records:
        date_key = r.created_at.strftime("%Y-%m-%d")
        if date_key not in date_scores:
            date_scores[date_key] = {"correct": 0, "total": 0, "attempts": 0}
        date_scores[date_key]["total"] += 1
        date_scores[date_key]["attempts"] += 1
        if r.is_correct:
            date_scores[date_key]["correct"] += 1

    history = []
    accuracy_history = []
    cumulative_correct = 0
    cumulative_total = 0
    for date_key in sorted(date_scores.keys()):
        d = date_scores[date_key]
        cumulative_correct += d["correct"]
        cumulative_total += d["total"]
        score = (cumulative_correct / max(cumulative_total, 1)) * 100
        history.append(
            MasteryHistoryPoint(date=date_key, score=round(score, 1), attempts=d["attempts"])
        )
        accuracy_history.append({
            "date": date_key,
            "accuracy_pct": round(d["correct"] / max(d["total"], 1) * 100, 1),
        })

    # Related topics (siblings in the same parent)
    related = []
    if kp.parent_id:
        siblings = (
            db.query(KnowledgePoint)
            .filter(
                KnowledgePoint.parent_id == kp.parent_id,
                KnowledgePoint.id != kp_id,
            )
            .all()
        )
        for sib in siblings:
            sib_mastery = (
                db.query(MasteryScore)
                .filter(
                    MasteryScore.user_id == current_user.id,
                    MasteryScore.knowledge_point_id == sib.id,
                )
                .first()
            )
            related.append({
                "id": sib.id,
                "name": sib.name,
                "mastery": round(sib_mastery.score, 1) if sib_mastery else 0.0,
            })

    return MasteryDetailResponse(
        knowledge_point_id=kp.id,
        knowledge_point_name=kp.name,
        full_path=kp.full_path,
        current_score=current_score,
        history=history,
        accuracy_history=accuracy_history,
        related_topics=related,
    )


@router.get("/trends", response_model=TrendResponse)
def get_trends(
    period: str = Query("weekly", description="weekly or monthly"),
    weeks: int = Query(12, ge=1, le=52),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get question frequency and accuracy trends over time."""
    now = datetime.now(timezone.utc)
    delta = timedelta(weeks=1) if period == "weekly" else timedelta(days=30)

    periods = []
    for i in range(weeks - 1, -1, -1):
        end_date = now - timedelta(weeks=i) if period == "weekly" else now - timedelta(days=30 * i)
        start_date = end_date - delta

        records = (
            db.query(AnswerRecord)
            .filter(
                AnswerRecord.user_id == current_user.id,
                AnswerRecord.created_at >= start_date,
                AnswerRecord.created_at < end_date,
            )
            .all()
        )

        question_count = len(records)
        correct_count = sum(1 for r in records if r.is_correct)
        accuracy_pct = round(correct_count / max(question_count, 1) * 100, 1)

        # Top tags in this period
        tag_counts = {}
        for r in records:
            q = db.query(Question).filter(Question.id == r.question_id).first()
            if q and q.tags:
                for tag in q.tags:
                    kp = tag.knowledge_point
                    name = kp.name if kp else "Unknown"
                    tag_counts[name] = tag_counts.get(name, 0) + 1

        top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        # New KPs encountered in this period
        prev_kps = set()
        if i < weeks - 1:
            prev_records = (
                db.query(AnswerRecord)
                .filter(
                    AnswerRecord.user_id == current_user.id,
                    AnswerRecord.created_at < start_date,
                )
                .all()
            )
            prev_kps = {r.knowledge_point_id for r in prev_records if r.knowledge_point_id}

        current_kps = {r.knowledge_point_id for r in records if r.knowledge_point_id}
        new_kps = current_kps - prev_kps

        label = start_date.strftime("%m/%d") + " - " + end_date.strftime("%m/%d")
        periods.append(
            TrendPeriodItem(
                label=label,
                start_date=start_date.strftime("%Y-%m-%d"),
                end_date=end_date.strftime("%Y-%m-%d"),
                question_count=question_count,
                correct_count=correct_count,
                accuracy_pct=accuracy_pct,
                top_tags=[{"name": name, "count": count} for name, count in top_tags],
                new_kps_encountered=len(new_kps),
            )
        )

    return TrendResponse(periods=periods)


@router.get("/weaknesses", response_model=WeaknessListResponse)
def get_weakness_list(
    limit: int = Query(5, ge=1, le=20),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the user's top weak areas."""
    weaknesses = get_weaknesses(current_user.id, db, limit=limit)

    return WeaknessListResponse(
        items=[
            WeaknessItemResponse(
                knowledge_point_id=w["knowledge_point_id"],
                name=w["name"],
                full_path=w["full_path"],
                score=w["score"],
                accuracy=w["accuracy"],
                total_attempts=w["total_attempts"],
                last_mistake_at=w["last_mistake_at"],
                mistake_types=w["mistake_types"],
            )
            for w in weaknesses
        ]
    )


@router.get("/recommendations", response_model=RecommendationListResponse)
def get_learning_recommendations(
    limit: int = Query(5, ge=1, le=10),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get learning recommendations based on weaknesses."""
    recs = get_recommendations(current_user.id, db, limit=limit)

    return RecommendationListResponse(
        items=[
            RecommendationItemResponse(
                knowledge_point_id=r["knowledge_point_id"],
                name=r["name"],
                full_path=r["full_path"],
                current_score=r["current_score"],
                reasoning=r["reasoning"],
                suggested_actions=[
                    SuggestedAction(**a) for a in r["suggested_actions"]
                ],
            )
            for r in recs
        ]
    )


@router.get("/mistake-notebook", response_model=MistakeNotebookResponse)
def get_mistake_notebook(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    knowledge_point_id: int | None = Query(None),
    mistake_type: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    search: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the user's mistake notebook (错题本) with pagination and filters."""
    import math as _math

    query = db.query(AnswerRecord).filter(
        AnswerRecord.user_id == current_user.id,
        AnswerRecord.is_correct == False,
    )

    if knowledge_point_id:
        query = query.filter(AnswerRecord.knowledge_point_id == knowledge_point_id)
    if mistake_type:
        query = query.filter(AnswerRecord.mistake_type == mistake_type)
    if date_from:
        query = query.filter(AnswerRecord.created_at >= datetime.fromisoformat(date_from))
    if date_to:
        query = query.filter(AnswerRecord.created_at <= datetime.fromisoformat(date_to))

    total = query.count()
    pages = max(1, _math.ceil(total / per_page))
    offset = (page - 1) * per_page

    records = (
        query.order_by(AnswerRecord.created_at.desc())
        .offset(offset)
        .limit(per_page)
        .all()
    )

    items = []
    for r in records:
        # Get question content
        q = db.query(Question).filter(Question.id == r.question_id).first()
        question_content = q.content if q else ""

        # Apply search filter in Python (couldn't join easily)
        if search and search.lower() not in question_content.lower():
            continue

        # Get KP name
        kp_name = None
        if r.knowledge_point_id:
            kp = db.query(KnowledgePoint).filter(
                KnowledgePoint.id == r.knowledge_point_id
            ).first()
            kp_name = kp.name if kp else None

        items.append(
            MistakeNotebookItem(
                id=r.id,
                question_content=question_content,
                knowledge_point_name=kp_name,
                user_answer=r.user_answer,
                expected_answer=r.expected_answer,
                mistake_type=r.mistake_type,
                is_correct=r.is_correct,
                created_at=r.created_at,
            )
        )

    return MistakeNotebookResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/summary", response_model=SummaryResponse)
def get_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get an overall learning summary."""
    # Total questions
    total_questions = (
        db.query(Question).filter(Question.user_id == current_user.id).count()
    )

    # Answer stats
    all_records = (
        db.query(AnswerRecord)
        .filter(AnswerRecord.user_id == current_user.id)
        .all()
    )
    total_correct = sum(1 for r in all_records if r.is_correct)
    overall_accuracy = round(
        total_correct / max(len(all_records), 1) * 100, 1
    )

    # Sessions
    total_sessions = (
        db.query(LearningSession)
        .filter(LearningSession.user_id == current_user.id)
        .count()
    )
    total_study_minutes = (
        db.query(func.coalesce(func.sum(LearningSession.duration_minutes), 0))
        .filter(LearningSession.user_id == current_user.id)
        .scalar()
    )

    # Mastery distribution
    mastery_records = (
        db.query(MasteryScore)
        .filter(MasteryScore.user_id == current_user.id)
        .all()
    )
    distribution = {
        "0-20": 0, "21-40": 0, "41-60": 0, "61-80": 0, "81-100": 0,
    }
    for m in mastery_records:
        if m.score <= 20:
            distribution["0-20"] += 1
        elif m.score <= 40:
            distribution["21-40"] += 1
        elif m.score <= 60:
            distribution["41-60"] += 1
        elif m.score <= 80:
            distribution["61-80"] += 1
        else:
            distribution["81-100"] += 1

    # Strongest/weakest areas
    sorted_mastery = sorted(mastery_records, key=lambda m: m.score, reverse=True)
    strongest = []
    for m in sorted_mastery[:3]:
        kp = db.query(KnowledgePoint).filter(KnowledgePoint.id == m.knowledge_point_id).first()
        if kp:
            strongest.append({"name": kp.name, "full_path": kp.full_path, "score": round(m.score, 1)})

    weakest = []
    for m in sorted_mastery[-3:]:
        kp = db.query(KnowledgePoint).filter(KnowledgePoint.id == m.knowledge_point_id).first()
        if kp:
            weakest.append({"name": kp.name, "full_path": kp.full_path, "score": round(m.score, 1)})

    # Streak days (consecutive days with at least one correct answer)
    streak_days = _compute_streak_days(current_user.id, db)

    # Topics explored
    topics_explored = len(mastery_records)

    return SummaryResponse(
        total_questions=total_questions,
        total_correct=total_correct,
        overall_accuracy=overall_accuracy,
        total_sessions=total_sessions,
        total_study_minutes=total_study_minutes or 0,
        mastery_distribution=distribution,
        strongest_areas=strongest,
        weakest_areas=weakest,
        streak_days=streak_days,
        topics_explored=topics_explored,
    )


def _compute_streak_days(user_id: int, db: Session) -> int:
    """Compute the current consecutive-day streak of correct answers."""
    records = (
        db.query(AnswerRecord)
        .filter(
            AnswerRecord.user_id == user_id,
            AnswerRecord.is_correct == True,
        )
        .order_by(AnswerRecord.created_at.desc())
        .all()
    )

    if not records:
        return 0

    streak = 0
    current_date = datetime.now(timezone.utc).date()

    for r in records:
        r_date = r.created_at.date() if hasattr(r.created_at, 'date') else r.created_at.date()
        if r_date == current_date:
            streak += 1
            current_date = current_date - timedelta(days=1)
        elif r_date == current_date - timedelta(days=1):
            streak += 1
            current_date = r_date
        else:
            break

    return streak
