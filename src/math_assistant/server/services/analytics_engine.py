"""Analytics engine: mastery scoring, trend analysis, weakness detection,
and learning recommendations.

Mastery Score Algorithm
-----------------------
Uses a weighted formula combining recency, consistency, and streak:

    RECENCY_WEIGHT   = 0.5  — recent answers matter more
    CONSISTENCY_WEIGHT = 0.3 — long-term accuracy
    STREAK_BONUS     = 0.2  — consecutive correct reward

    score = 0.5 * recent_accuracy * 100
          + 0.3 * overall_accuracy * 100
          + 0.2 * min(streak / 10, 1.0) * 100

    confidence = min(total_attempts / 20, 1.0)

Weakness Detection
------------------
    weakness_score = (100 - mastery_score) * log(total_attempts + 1) * recency_penalty
    recency_penalty = 1.5 if any mistake in last 7 days, else 1.0

Learning Recommendations
-------------------------
Prioritizes confirmed weaknesses (score < 50, confidence > 0.3),
checks prerequisites, and assigns action types based on mastery level.
"""

import math
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from math_assistant.server.models.answer_record import AnswerRecord
from math_assistant.server.models.knowledge_point import KnowledgePoint
from math_assistant.server.models.mastery import MasteryScore
from math_assistant.server.models.question import Question
from math_assistant.server.models.question_tag import QuestionTag
from math_assistant.server.models.learning_session import LearningSession

# Weights for mastery score calculation
RECENCY_WEIGHT = 0.5
CONSISTENCY_WEIGHT = 0.3
STREAK_BONUS = 0.2
STREAK_CAP = 10  # Max streak for bonus
CONFIDENCE_THRESHOLD = 20  # Attempts needed for full confidence


def update_mastery_score(
    user_id: int, knowledge_point_id: int, db: Session
) -> dict | None:
    """Recalculate and persist the mastery score for a user+knowledge_point.

    Called after every AnswerRecord creation.

    Args:
        user_id: The user's ID.
        knowledge_point_id: The knowledge point's ID.
        db: Database session.

    Returns:
        Dict with old_score, new_score, or None if no data exists.
    """
    # Get all answer records for this user+KP
    all_records = (
        db.query(AnswerRecord)
        .filter(
            AnswerRecord.user_id == user_id,
            AnswerRecord.knowledge_point_id == knowledge_point_id,
        )
        .order_by(AnswerRecord.created_at.desc())
        .all()
    )

    total_attempts = len(all_records)
    if total_attempts == 0:
        return None

    correct_attempts = sum(1 for r in all_records if r.is_correct)

    # Recent attempts (last 30 days)
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    recent_attempts = sum(
        1 for r in all_records
        if r.created_at.replace(tzinfo=timezone.utc) >= thirty_days_ago
    )
    recent_correct = sum(
        1 for r in all_records
        if r.is_correct and r.created_at.replace(tzinfo=timezone.utc) >= thirty_days_ago
    )

    # Streak: count consecutive correct from most recent
    streak = 0
    for r in all_records:
        if r.is_correct:
            streak += 1
        else:
            break

    # Calculate score
    recent_accuracy = recent_correct / max(recent_attempts, 1)
    overall_accuracy = correct_attempts / max(total_attempts, 1)
    streak_factor = min(streak / STREAK_CAP, 1.0)

    score = (
        RECENCY_WEIGHT * recent_accuracy * 100
        + CONSISTENCY_WEIGHT * overall_accuracy * 100
        + STREAK_BONUS * streak_factor * 100
    )

    confidence = min(total_attempts / CONFIDENCE_THRESHOLD, 1.0)

    # Upsert MasteryScore
    mastery = (
        db.query(MasteryScore)
        .filter(
            MasteryScore.user_id == user_id,
            MasteryScore.knowledge_point_id == knowledge_point_id,
        )
        .first()
    )

    old_score = mastery.score if mastery else 0.0

    if mastery:
        mastery.score = score
        mastery.confidence = confidence
        mastery.total_attempts = total_attempts
        mastery.correct_attempts = correct_attempts
        mastery.recent_attempts = recent_attempts
        mastery.recent_correct = recent_correct
        mastery.streak = streak
        mastery.last_attempted_at = all_records[0].created_at if all_records else None
    else:
        mastery = MasteryScore(
            user_id=user_id,
            knowledge_point_id=knowledge_point_id,
            score=score,
            confidence=confidence,
            total_attempts=total_attempts,
            correct_attempts=correct_attempts,
            recent_attempts=recent_attempts,
            recent_correct=recent_correct,
            streak=streak,
            last_attempted_at=all_records[0].created_at if all_records else None,
        )
        db.add(mastery)

    db.commit()

    return {"old_score": old_score, "new_score": score}


def compute_mastery_trend(user_id: int, kp_id: int, db: Session) -> str:
    """Determine mastery trend: 'improving', 'stable', or 'declining'.

    Compares the most recent 4-week window to the prior 4-week window.
    A >5 percentage point change = improving/declining, else stable.
    """
    now = datetime.now(timezone.utc)
    four_weeks_ago = now - timedelta(weeks=4)
    eight_weeks_ago = now - timedelta(weeks=8)

    recent = (
        db.query(AnswerRecord)
        .filter(
            AnswerRecord.user_id == user_id,
            AnswerRecord.knowledge_point_id == kp_id,
            AnswerRecord.created_at >= four_weeks_ago,
        )
        .all()
    )
    prior = (
        db.query(AnswerRecord)
        .filter(
            AnswerRecord.user_id == user_id,
            AnswerRecord.knowledge_point_id == kp_id,
            AnswerRecord.created_at >= eight_weeks_ago,
            AnswerRecord.created_at < four_weeks_ago,
        )
        .all()
    )

    recent_acc = sum(1 for r in recent if r.is_correct) / max(len(recent), 1) * 100
    prior_acc = sum(1 for r in prior if r.is_correct) / max(len(prior), 1) * 100

    if len(prior) == 0:
        return "stable"

    delta = recent_acc - prior_acc
    if delta > 5:
        return "improving"
    elif delta < -5:
        return "declining"
    return "stable"


def compute_weakness_score(
    mastery_score: float,
    total_attempts: int,
    has_recent_mistake: bool,
) -> float:
    """Compute the composite weakness score.

    Higher = more concerning weakness.
    """
    recency_penalty = 1.5 if has_recent_mistake else 1.0
    return (100 - mastery_score) * math.log(total_attempts + 1) * recency_penalty


def get_weaknesses(
    user_id: int, db: Session, limit: int = 5
) -> list[dict]:
    """Get the user's top weak areas ranked by weakness score.

    Returns:
        List of dicts with weakness details, sorted by weakness_score descending.
    """
    # Get mastery records with confidence > 0 (has data)
    mastery_records = (
        db.query(MasteryScore)
        .filter(
            MasteryScore.user_id == user_id,
            MasteryScore.total_attempts > 0,
        )
        .all()
    )

    now = datetime.now(timezone.utc)
    seven_days_ago = now - timedelta(days=7)

    weaknesses = []
    for m in mastery_records:
        kp = db.query(KnowledgePoint).filter(KnowledgePoint.id == m.knowledge_point_id).first()
        if not kp:
            continue

        # Check if there was a mistake in the last 7 days
        has_recent_mistake = (
            db.query(AnswerRecord)
            .filter(
                AnswerRecord.user_id == user_id,
                AnswerRecord.knowledge_point_id == m.knowledge_point_id,
                AnswerRecord.is_correct == False,
                AnswerRecord.created_at >= seven_days_ago,
            )
            .first()
            is not None
        )

        weakness = compute_weakness_score(m.score, m.total_attempts, has_recent_mistake)

        # Get mistake type breakdown
        mistake_types = (
            db.query(
                AnswerRecord.mistake_type,
                func.count(AnswerRecord.id).label("count"),
            )
            .filter(
                AnswerRecord.user_id == user_id,
                AnswerRecord.knowledge_point_id == m.knowledge_point_id,
                AnswerRecord.is_correct == False,
            )
            .group_by(AnswerRecord.mistake_type)
            .all()
        )

        accuracy = (
            m.correct_attempts / max(m.total_attempts, 1) * 100
        )

        last_mistake = (
            db.query(AnswerRecord.created_at)
            .filter(
                AnswerRecord.user_id == user_id,
                AnswerRecord.knowledge_point_id == m.knowledge_point_id,
                AnswerRecord.is_correct == False,
            )
            .order_by(AnswerRecord.created_at.desc())
            .first()
        )

        weaknesses.append({
            "knowledge_point_id": m.knowledge_point_id,
            "name": kp.name,
            "full_path": kp.full_path,
            "score": m.score,
            "accuracy": round(accuracy, 1),
            "total_attempts": m.total_attempts,
            "weakness_score": round(weakness, 2),
            "last_mistake_at": last_mistake[0] if last_mistake else None,
            "mistake_types": [
                {"type": mt[0] or "unknown", "count": mt[1]}
                for mt in mistake_types
            ],
        })

    # Sort by weakness_score descending, limit
    weaknesses.sort(key=lambda w: w["weakness_score"], reverse=True)
    return weaknesses[:limit]


def get_recommendations(
    user_id: int, db: Session, limit: int = 5
) -> list[dict]:
    """Generate learning recommendations based on weaknesses and prerequisites.

    Algorithm:
    1. Find confirmed weaknesses (score < 50, confidence > 0.3)
    2. Check prerequisites — if a prerequisite also has low mastery,
       recommend prerequisite review first
    3. Rank by weakness_score * importance
    4. Assign action types based on mastery level

    Returns:
        List of recommendation dicts sorted by priority.
    """
    weaknesses = get_weaknesses(user_id, db, limit=len(
        db.query(MasteryScore).filter(MasteryScore.user_id == user_id).all()
    ))

    # Filter to confirmed weaknesses
    confirmed = [w for w in weaknesses if w["score"] < 50 and w["total_attempts"] >= 3]

    if not confirmed:
        # If no confirmed weaknesses, suggest review for lowest-score topics
        all_mastery = (
            db.query(MasteryScore)
            .filter(MasteryScore.user_id == user_id)
            .order_by(MasteryScore.score.asc())
            .limit(limit)
            .all()
        )
        recommendations = []
        seen_ids = set()
        for m in all_mastery:
            kp = db.query(KnowledgePoint).filter(KnowledgePoint.id == m.knowledge_point_id).first()
            if not kp or kp.id in seen_ids:
                continue
            seen_ids.add(kp.id)
            recommendations.append(_build_recommendation(kp, m, db))
        return recommendations[:limit]

    # Build recommendations prioritizing prerequisites
    recommendations = []
    seen_ids = set()

    for w in sorted(confirmed, key=lambda w: w["weakness_score"] * _get_importance(w["knowledge_point_id"], db), reverse=True):
        kp = db.query(KnowledgePoint).filter(KnowledgePoint.id == w["knowledge_point_id"]).first()
        if not kp or kp.id in seen_ids:
            continue
        seen_ids.add(kp.id)

        # Check if any prerequisites are also weak
        if kp.prerequisite_ids:
            for prereq_id in kp.prerequisite_ids:
                if prereq_id in seen_ids:
                    continue
                prereq_mastery = (
                    db.query(MasteryScore)
                    .filter(
                        MasteryScore.user_id == user_id,
                        MasteryScore.knowledge_point_id == prereq_id,
                    )
                    .first()
                )
                if prereq_mastery and prereq_mastery.score < 50:
                    prereq_kp = db.query(KnowledgePoint).filter(
                        KnowledgePoint.id == prereq_id
                    ).first()
                    if prereq_kp:
                        seen_ids.add(prereq_id)
                        recommendations.append(
                            _build_recommendation(prereq_kp, prereq_mastery, db, is_prereq=True)
                        )

        recommendations.append(_build_recommendation(kp, None, db))

        if len(recommendations) >= limit:
            break

    return recommendations[:limit]


def _get_importance(kp_id: int, db: Session) -> float:
    """Get the importance value of a knowledge point."""
    kp = db.query(KnowledgePoint).filter(KnowledgePoint.id == kp_id).first()
    return kp.importance if kp else 1.0


def _build_recommendation(
    kp: KnowledgePoint,
    mastery: MasteryScore | None,
    db: Session,
    is_prereq: bool = False,
) -> dict:
    """Build a single recommendation dict for a knowledge point."""
    score = mastery.score if mastery else 0.0
    total_attempts = mastery.total_attempts if mastery else 0

    # Determine action type
    if is_prereq:
        action_type = "prerequisite_review"
        action_desc = f"Review '{kp.name}' first — it's a prerequisite for topics you're struggling with"
    elif score < 30 and total_attempts < 5:
        action_type = "review_concept"
        action_desc = f"Study '{kp.name}' fundamentals — you haven't attempted enough practice yet"
    elif 30 <= score < 60:
        action_type = "practice_problems"
        action_desc = f"Focus on '{kp.name}' practice problems to improve accuracy"
    elif score >= 70:
        action_type = "advanced_challenge"
        # Find next topics in the hierarchy
        children = kp.children if kp.children else []
        child_names = ", ".join(c.name for c in children[:3]) if children else "advanced topics"
        action_desc = f"You're doing well! Try moving on to: {child_names}"
    else:
        action_type = "practice_problems"
        action_desc = f"Continue practicing '{kp.name}' to build consistency"

    reasoning = (
        f"Current mastery: {score:.0f}/100 from {total_attempts} attempts. "
        f"{'This is a prerequisite for topics you are struggling with. ' if is_prereq else ''}"
        f"Suggested: {action_desc}"
    )

    return {
        "knowledge_point_id": kp.id,
        "name": kp.name,
        "full_path": kp.full_path,
        "current_score": score,
        "reasoning": reasoning,
        "suggested_actions": [{"action_type": action_type, "description": action_desc}],
    }
