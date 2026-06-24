"""QuestionTag ORM model — links questions to knowledge points.

Carries metadata about the tag: its source (auto vs manual),
confidence level, and whether the user corrected it.
"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from math_assistant.server.database import Base


class QuestionTag(Base):
    __tablename__ = "question_tags"
    __table_args__ = (
        UniqueConstraint("question_id", "knowledge_point_id", name="uq_question_kp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    question_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("questions.id"), nullable=False, index=True
    )
    knowledge_point_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("knowledge_points.id"), nullable=False, index=True
    )
    confidence: Mapped[float] = mapped_column(
        Float, nullable=False, default=1.0
    )
    source: Mapped[str] = mapped_column(
        String(8), nullable=False, default="auto"
    )
    is_user_corrected: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    tagged_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    # Relationships
    question = relationship("Question", back_populates="tags")
    knowledge_point = relationship("KnowledgePoint", back_populates="tags")

    def __repr__(self) -> str:
        return (
            f"<QuestionTag(q_id={self.question_id}, kp_id={self.knowledge_point_id}, "
            f"source='{self.source}', confidence={self.confidence:.2f})>"
        )
