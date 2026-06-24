"""MasteryScore ORM model — pre-computed per-user, per-knowledge-point mastery.

Updated after every answer record to avoid expensive aggregation
on analytics reads.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from math_assistant.server.database import Base


class MasteryScore(Base):
    __tablename__ = "mastery_scores"
    __table_args__ = (
        UniqueConstraint("user_id", "knowledge_point_id", name="uq_user_kp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    knowledge_point_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("knowledge_points.id"), nullable=False, index=True
    )
    score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    correct_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    recent_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    recent_correct: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    streak: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_attempted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user = relationship("User", back_populates="mastery_scores")
    knowledge_point = relationship("KnowledgePoint", back_populates="mastery_scores")

    def __repr__(self) -> str:
        return (
            f"<MasteryScore(user_id={self.user_id}, kp_id={self.knowledge_point_id}, "
            f"score={self.score:.1f}, confidence={self.confidence:.2f})>"
        )
