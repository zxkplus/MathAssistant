"""Question ORM model — stores each question a user asks."""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from math_assistant.server.database import Base


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    session_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("learning_sessions.id"), nullable=True, index=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    subject: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, index=True
    )
    difficulty: Mapped[Optional[str]] = mapped_column(
        String(16), nullable=True
    )
    source: Mapped[str] = mapped_column(
        String(16), nullable=False, default="manual"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    # Relationships
    user = relationship("User", back_populates="questions")
    session = relationship("LearningSession", back_populates="questions")
    tags = relationship(
        "QuestionTag", back_populates="question", cascade="all, delete-orphan"
    )
    answer_records = relationship(
        "AnswerRecord", back_populates="question", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"<Question(id={self.id}, user_id={self.user_id}, content='{preview}')>"
