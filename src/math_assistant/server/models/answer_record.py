"""AnswerRecord ORM model — the "wrong answer notebook" (错题本).

Records the result of each answer attempt for mastery tracking.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from math_assistant.server.database import Base


class AnswerRecord(Base):
    __tablename__ = "answer_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    question_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("questions.id"), nullable=False, index=True
    )
    knowledge_point_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("knowledge_points.id"), nullable=True, index=True
    )
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    user_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expected_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mistake_type: Mapped[Optional[str]] = mapped_column(
        String(32), nullable=True, index=True
    )
    time_spent_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    difficulty_at_time: Mapped[Optional[str]] = mapped_column(
        String(16), nullable=True
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    # Relationships
    user = relationship("User", back_populates="answer_records")
    question = relationship("Question", back_populates="answer_records")
    # KnowledgePoint relationship is read-only via FK

    def __repr__(self) -> str:
        return (
            f"<AnswerRecord(id={self.id}, user_id={self.user_id}, "
            f"correct={self.is_correct}, mistake='{self.mistake_type}')>"
        )
