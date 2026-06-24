"""Pydantic schemas for knowledge point endpoints."""

from datetime import datetime

from pydantic import BaseModel, Field


class KnowledgePointCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    parent_id: int | None = None
    description: str | None = None
    importance: float = Field(1.0, ge=0.0, le=1.0)
    prerequisite_ids: list[int] | None = None


class KnowledgePointResponse(BaseModel):
    id: int
    parent_id: int | None = None
    name: str
    full_path: str
    depth: int
    description: str | None = None
    importance: float
    prerequisite_ids: list[int] | None = None
    children_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class KnowledgePointTreeResponse(BaseModel):
    """Recursive tree node for the full hierarchy."""
    id: int
    name: str
    full_path: str
    depth: int
    description: str | None = None
    children: list["KnowledgePointTreeResponse"] = []

    model_config = {"from_attributes": True}


class SeedResponse(BaseModel):
    created: int
    skipped: int
