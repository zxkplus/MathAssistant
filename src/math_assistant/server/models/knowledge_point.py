"""KnowledgePoint ORM model — hierarchical taxonomy of math topics.

Uses an adjacency-list pattern (parent_id self-referential FK)
with a denormalized full_path column for efficient querying.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship


from math_assistant.server.database import Base


class KnowledgePoint(Base):
    __tablename__ = "knowledge_points"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    parent_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("knowledge_points.id"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(
        String(128), nullable=False, index=True
    )
    full_path: Mapped[str] = mapped_column(
        String(512), nullable=False, unique=True, index=True
    )
    depth: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    importance: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    prerequisite_ids: Mapped[Optional[list[int]]] = mapped_column(
        JSON, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    # Self-referential relationships
    parent = relationship(
        "KnowledgePoint", remote_side="KnowledgePoint.id", back_populates="children"
    )
    children = relationship(
        "KnowledgePoint", back_populates="parent", cascade="all, delete-orphan"
    )

    # Other relationships
    tags = relationship(
        "QuestionTag", back_populates="knowledge_point", cascade="all, delete-orphan"
    )
    mastery_scores = relationship(
        "MasteryScore", back_populates="knowledge_point", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<KnowledgePoint(id={self.id}, name='{self.name}', path='{self.full_path}')>"
