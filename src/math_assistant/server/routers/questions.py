"""Question router: CRUD, answer recording, and tag management."""

import math
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from math_assistant.server.database import get_db
from math_assistant.server.dependencies import get_current_user
from math_assistant.server.models.answer_record import AnswerRecord
from math_assistant.server.models.knowledge_point import KnowledgePoint
from math_assistant.server.models.question import Question
from math_assistant.server.models.question_tag import QuestionTag
from math_assistant.server.models.user import User
from math_assistant.server.schemas.question import (
    AnswerCreateRequest,
    AnswerResponse,
    AnswerRecordResponse,
    MasteryUpdateItem,
    QuestionCreate,
    QuestionListResponse,
    QuestionResponse,
    QuestionTagResponse,
    TagUpdateRequest,
)

router = APIRouter()


def _tag_to_response(tag: QuestionTag) -> QuestionTagResponse:
    """Convert a QuestionTag ORM object to response, including KP name."""
    kp_name = tag.knowledge_point.name if tag.knowledge_point else ""
    return QuestionTagResponse(
        id=tag.id,
        knowledge_point_id=tag.knowledge_point_id,
        knowledge_point_name=kp_name,
        confidence=tag.confidence,
        source=tag.source,
        is_user_corrected=tag.is_user_corrected,
        tagged_at=tag.tagged_at,
    )


def _ar_to_response(ar: AnswerRecord) -> AnswerRecordResponse:
    """Convert an AnswerRecord ORM object to response."""
    return AnswerRecordResponse(
        id=ar.id,
        user_id=ar.user_id,
        question_id=ar.question_id,
        knowledge_point_id=ar.knowledge_point_id,
        is_correct=ar.is_correct,
        user_answer=ar.user_answer,
        expected_answer=ar.expected_answer,
        mistake_type=ar.mistake_type,
        time_spent_seconds=ar.time_spent_seconds,
        created_at=ar.created_at,
    )


def _question_to_response(q: Question) -> QuestionResponse:
    """Convert a Question ORM object to response with tags and answer records."""
    tags = [_tag_to_response(t) for t in q.tags] if q.tags else []
    records = [_ar_to_response(r) for r in q.answer_records] if q.answer_records else []
    # Check if auto-tagging is pending (no tags yet, recent question)
    tags_pending = len(tags) == 0 and (datetime.utcnow() - q.created_at).seconds < 30

    return QuestionResponse(
        id=q.id,
        user_id=q.user_id,
        session_id=q.session_id,
        content=q.content,
        subject=q.subject,
        difficulty=q.difficulty,
        source=q.source,
        tags=tags,
        answer_records=records,
        tags_pending=tags_pending,
        created_at=q.created_at,
    )


@router.post("", response_model=QuestionResponse, status_code=status.HTTP_201_CREATED)
def create_question(
    body: QuestionCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Submit a new question. Auto-tagging runs in the background."""
    question = Question(
        user_id=current_user.id,
        session_id=body.session_id,
        content=body.content,
        source=body.source,
    )
    db.add(question)
    db.commit()
    db.refresh(question)

    # Trigger async auto-tagging
    from math_assistant.server.services.tagging_service import auto_tag_question
    background_tasks.add_task(auto_tag_question, question.id, db)

    return _question_to_response(question)


@router.get("/", response_model=QuestionListResponse)
def list_questions(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    tag: int | None = Query(None, description="Filter by knowledge point ID"),
    difficulty: str | None = Query(None, description="Filter by difficulty"),
    subject: str | None = Query(None, description="Filter by subject"),
    date_from: str | None = Query(None, description="Start date (ISO format)"),
    date_to: str | None = Query(None, description="End date (ISO format)"),
    search: str | None = Query(None, description="Search in question content"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List questions for the current user with pagination and filters."""
    query = db.query(Question).filter(Question.user_id == current_user.id)

    if tag is not None:
        query = query.join(Question.tags).filter(
            QuestionTag.knowledge_point_id == tag
        )
    if difficulty:
        query = query.filter(Question.difficulty == difficulty)
    if subject:
        query = query.filter(Question.subject == subject)
    if date_from:
        query = query.filter(Question.created_at >= datetime.fromisoformat(date_from))
    if date_to:
        query = query.filter(Question.created_at <= datetime.fromisoformat(date_to))
    if search:
        query = query.filter(Question.content.ilike(f"%{search}%"))

    total = query.count()
    pages = max(1, math.ceil(total / per_page))
    offset = (page - 1) * per_page

    questions = (
        query.order_by(Question.created_at.desc())
        .offset(offset)
        .limit(per_page)
        .all()
    )

    return QuestionListResponse(
        items=[_question_to_response(q) for q in questions],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.get("/{question_id}", response_model=QuestionResponse)
def get_question(
    question_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a single question by ID."""
    q = (
        db.query(Question)
        .filter(Question.id == question_id, Question.user_id == current_user.id)
        .first()
    )
    if not q:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
    return _question_to_response(q)


@router.put("/{question_id}", response_model=QuestionResponse)
def update_question(
    question_id: int,
    body: QuestionCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a question's content. Re-triggers auto-tagging if content changed."""
    q = (
        db.query(Question)
        .filter(Question.id == question_id, Question.user_id == current_user.id)
        .first()
    )
    if not q:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")

    content_changed = q.content != body.content
    q.content = body.content
    if body.source:
        q.source = body.source
    if body.session_id is not None:
        q.session_id = body.session_id
    db.commit()
    db.refresh(q)

    if content_changed:
        from math_assistant.server.services.tagging_service import auto_tag_question
        background_tasks.add_task(auto_tag_question, q.id, db)

    return _question_to_response(q)


@router.put("/{question_id}/tags", response_model=QuestionResponse)
def update_question_tags(
    question_id: int,
    body: TagUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Manually correct tags for a question.

    Replaces all existing tags with the user-specified set.
    Sets source='manual', confidence=1.0, is_user_corrected=True.
    """
    q = (
        db.query(Question)
        .filter(Question.id == question_id, Question.user_id == current_user.id)
        .first()
    )
    if not q:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")

    # Delete existing tags
    db.query(QuestionTag).filter(QuestionTag.question_id == question_id).delete()

    # Create new manual tags
    for tag_item in body.tags:
        # Verify KP exists
        kp = db.query(KnowledgePoint).filter(
            KnowledgePoint.id == tag_item.knowledge_point_id
        ).first()
        if not kp:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Knowledge point {tag_item.knowledge_point_id} not found",
            )

        tag = QuestionTag(
            question_id=question_id,
            knowledge_point_id=tag_item.knowledge_point_id,
            confidence=1.0,
            source="manual",
            is_user_corrected=True,
        )
        db.add(tag)

    db.commit()
    db.refresh(q)
    return _question_to_response(q)


@router.delete("/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_question(
    question_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a question and all associated tags and answer records."""
    q = (
        db.query(Question)
        .filter(Question.id == question_id, Question.user_id == current_user.id)
        .first()
    )
    if not q:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")

    db.delete(q)
    db.commit()
    return None


@router.post("/{question_id}/answer", response_model=AnswerResponse)
def record_answer(
    question_id: int,
    body: AnswerCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Record an answer result for a question.

    Creates an AnswerRecord and triggers mastery recalculation.
    """
    q = (
        db.query(Question)
        .filter(Question.id == question_id, Question.user_id == current_user.id)
        .first()
    )
    if not q:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")

    # Determine the knowledge point for this answer
    kp_id = body.knowledge_point_id
    if kp_id is None and q.tags:
        # Use the first tag's KP as default
        kp_id = q.tags[0].knowledge_point_id

    record = AnswerRecord(
        user_id=current_user.id,
        question_id=question_id,
        knowledge_point_id=kp_id,
        is_correct=body.is_correct,
        user_answer=body.user_answer,
        expected_answer=body.expected_answer,
        mistake_type=body.mistake_type if not body.is_correct else None,
        time_spent_seconds=body.time_spent_seconds,
        difficulty_at_time=body.difficulty_at_time,
        notes=body.notes,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    # Recalculate mastery for affected knowledge points
    mastery_updates = []
    affected_kp_ids = {kp_id} if kp_id else set()
    # Also include all tags' KPs
    for tag in q.tags:
        affected_kp_ids.add(tag.knowledge_point_id)

    from math_assistant.server.services.analytics_engine import update_mastery_score
    for affected_kp_id in affected_kp_ids:
        if affected_kp_id is None:
            continue
        result = update_mastery_score(current_user.id, affected_kp_id, db)
        if result:
            mastery_updates.append(
                MasteryUpdateItem(
                    knowledge_point_id=affected_kp_id,
                    old_score=result["old_score"],
                    new_score=result["new_score"],
                )
            )

    # Update session counters if the question belongs to a session
    if q.session_id:
        from math_assistant.server.models.learning_session import LearningSession
        session = db.query(LearningSession).filter(
            LearningSession.id == q.session_id
        ).first()
        if session:
            session.question_count = (
                db.query(AnswerRecord)
                .join(Question)
                .filter(
                    Question.session_id == q.session_id,
                    AnswerRecord.user_id == current_user.id,
                )
                .count()
            )
            session.correct_count = (
                db.query(AnswerRecord)
                .join(Question)
                .filter(
                    Question.session_id == q.session_id,
                    AnswerRecord.user_id == current_user.id,
                    AnswerRecord.is_correct == True,
                )
                .count()
            )
            db.commit()

    return AnswerResponse(
        answer_record_id=record.id,
        mastery_updates=mastery_updates,
    )
