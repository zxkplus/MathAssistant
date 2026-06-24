"""Pydantic schemas for question endpoints."""

from datetime import datetime

from pydantic import BaseModel, Field


class QuestionCreate(BaseModel):
    content: str = Field(..., min_length=1, description="The question text")
    source: str = Field("manual", max_length=16)
    session_id: int | None = None


class TagItem(BaseModel):
    knowledge_point_id: int


class TagUpdateRequest(BaseModel):
    tags: list[TagItem]


class QuestionTagResponse(BaseModel):
    id: int
    knowledge_point_id: int
    knowledge_point_name: str = ""
    confidence: float
    source: str
    is_user_corrected: bool
    tagged_at: datetime

    model_config = {"from_attributes": True}


class AnswerRecordResponse(BaseModel):
    id: int
    user_id: int
    question_id: int
    knowledge_point_id: int | None = None
    is_correct: bool
    user_answer: str | None = None
    expected_answer: str | None = None
    mistake_type: str | None = None
    time_spent_seconds: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class QuestionResponse(BaseModel):
    id: int
    user_id: int
    session_id: int | None = None
    content: str
    subject: str | None = None
    difficulty: str | None = None
    source: str
    tags: list[QuestionTagResponse] = []
    answer_records: list[AnswerRecordResponse] = []
    tags_pending: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


class QuestionListResponse(BaseModel):
    items: list[QuestionResponse]
    total: int
    page: int
    per_page: int
    pages: int


class AnswerCreateRequest(BaseModel):
    is_correct: bool
    user_answer: str | None = None
    expected_answer: str | None = None
    mistake_type: str | None = Field(
        None, max_length=32,
        description="conceptual, calculation, misreading, careless, unknown",
    )
    time_spent_seconds: int | None = None
    knowledge_point_id: int | None = None
    difficulty_at_time: str | None = None
    notes: str | None = None


class MasteryUpdateItem(BaseModel):
    knowledge_point_id: int
    old_score: float
    new_score: float


class AnswerResponse(BaseModel):
    answer_record_id: int
    mastery_updates: list[MasteryUpdateItem] = []
