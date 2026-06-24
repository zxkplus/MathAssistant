"""Pydantic schemas for analytics endpoints."""

from datetime import datetime

from pydantic import BaseModel


class MasteryItemResponse(BaseModel):
    knowledge_point_id: int
    knowledge_point_name: str
    full_path: str
    score: float
    confidence: float
    total_attempts: int
    correct_attempts: int
    streak: int
    last_attempted_at: datetime | None = None
    trend: str  # "improving", "stable", "declining"


class MasteryListResponse(BaseModel):
    items: list[MasteryItemResponse]
    overall_score: float


class MasteryHistoryPoint(BaseModel):
    date: str
    score: float
    attempts: int


class MasteryDetailResponse(BaseModel):
    knowledge_point_id: int
    knowledge_point_name: str
    full_path: str
    current_score: float
    history: list[MasteryHistoryPoint] = []
    accuracy_history: list[dict] = []
    related_topics: list[dict] = []


class TrendPeriodItem(BaseModel):
    label: str
    start_date: str
    end_date: str
    question_count: int
    correct_count: int
    accuracy_pct: float
    top_tags: list[dict] = []
    new_kps_encountered: int


class TrendResponse(BaseModel):
    periods: list[TrendPeriodItem]


class WeaknessItemResponse(BaseModel):
    knowledge_point_id: int
    name: str
    full_path: str
    score: float
    accuracy: float
    total_attempts: int
    last_mistake_at: datetime | None = None
    mistake_types: list[dict] = []


class WeaknessListResponse(BaseModel):
    items: list[WeaknessItemResponse]


class SuggestedAction(BaseModel):
    action_type: str  # "review_concept", "practice_problems", "prerequisite_review", "advanced_challenge"
    description: str


class RecommendationItemResponse(BaseModel):
    knowledge_point_id: int
    name: str
    full_path: str
    current_score: float
    reasoning: str
    suggested_actions: list[SuggestedAction]


class RecommendationListResponse(BaseModel):
    items: list[RecommendationItemResponse]


class MistakeNotebookItem(BaseModel):
    id: int
    question_content: str
    knowledge_point_name: str | None = None
    user_answer: str | None = None
    expected_answer: str | None = None
    mistake_type: str | None = None
    is_correct: bool
    created_at: datetime


class MistakeNotebookResponse(BaseModel):
    items: list[MistakeNotebookItem]
    total: int
    page: int
    per_page: int


class SummaryResponse(BaseModel):
    total_questions: int
    total_correct: int
    overall_accuracy: float
    total_sessions: int
    total_study_minutes: int
    mastery_distribution: dict[str, int]
    strongest_areas: list[dict]
    weakest_areas: list[dict]
    streak_days: int
    topics_explored: int
