"""Router aggregation for the FastAPI app."""

from math_assistant.server.routers.auth import router as auth_router
from math_assistant.server.routers.knowledge_points import router as knowledge_points_router
from math_assistant.server.routers.questions import router as questions_router
from math_assistant.server.routers.analytics import router as analytics_router

__all__ = [
    "auth_router",
    "knowledge_points_router",
    "questions_router",
    "analytics_router",
]
