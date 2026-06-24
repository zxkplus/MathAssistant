"""Barrel imports for Pydantic schemas."""

from math_assistant.server.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    TokenResponse,
    UpdateProfileRequest,
    UserResponse,
)
from math_assistant.server.schemas.knowledge_point import (
    KnowledgePointCreate,
    KnowledgePointResponse,
    KnowledgePointTreeResponse,
    SeedResponse,
)
from math_assistant.server.schemas.question import (
    AnswerCreateRequest,
    AnswerResponse,
    AnswerRecordResponse,
    MasteryUpdateItem,
    QuestionCreate,
    QuestionListResponse,
    QuestionResponse,
    QuestionTagResponse,
    TagItem,
    TagUpdateRequest,
)
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

__all__ = [
    # Auth
    "ChangePasswordRequest",
    "LoginRequest",
    "LoginResponse",
    "RegisterRequest",
    "TokenResponse",
    "UpdateProfileRequest",
    "UserResponse",
    # Knowledge Points
    "KnowledgePointCreate",
    "KnowledgePointResponse",
    "KnowledgePointTreeResponse",
    "SeedResponse",
    # Questions
    "AnswerCreateRequest",
    "AnswerResponse",
    "AnswerRecordResponse",
    "MasteryUpdateItem",
    "QuestionCreate",
    "QuestionListResponse",
    "QuestionResponse",
    "QuestionTagResponse",
    "TagItem",
    "TagUpdateRequest",
    # Analytics
    "MasteryDetailResponse",
    "MasteryHistoryPoint",
    "MasteryItemResponse",
    "MasteryListResponse",
    "MistakeNotebookItem",
    "MistakeNotebookResponse",
    "RecommendationItemResponse",
    "RecommendationListResponse",
    "SuggestedAction",
    "SummaryResponse",
    "TrendPeriodItem",
    "TrendResponse",
    "WeaknessItemResponse",
    "WeaknessListResponse",
]
