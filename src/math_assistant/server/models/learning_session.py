"""LearningSession ORM model — tracks study sessions for trend analysis."""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from math_assistant.server.database import Base


class LearningSession(Base):
    __tablename__ = "learning_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    ended_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )
    question_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    correct_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_minutes: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )

    # Relationships
    user = relationship("User", back_populates="learning_sessions")
    questions = relationship("Question", back_populates="session")

    def __repr__(self) -> str:
        return (
            f"<LearningSession(id={self.id}, user_id={self.user_id}, "
            f"questions={self.question_count})>"
        )
