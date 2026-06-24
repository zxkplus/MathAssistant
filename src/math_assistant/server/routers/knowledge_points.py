"""Knowledge points router: CRUD, tree, and seed endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from math_assistant.server.database import get_db
from math_assistant.server.models.knowledge_point import KnowledgePoint
from math_assistant.server.schemas.knowledge_point import (
    KnowledgePointCreate,
    KnowledgePointResponse,
    KnowledgePointTreeResponse,
    SeedResponse,
)
from math_assistant.server.services.taxonomy_seed import seed_taxonomy

router = APIRouter()


def _kp_to_response(kp: KnowledgePoint) -> KnowledgePointResponse:
    """Convert a KnowledgePoint ORM object to a response schema."""
    children_count = len(kp.children) if kp.children else 0
    return KnowledgePointResponse(
        id=kp.id,
        parent_id=kp.parent_id,
        name=kp.name,
        full_path=kp.full_path,
        depth=kp.depth,
        description=kp.description,
        importance=kp.importance,
        prerequisite_ids=kp.prerequisite_ids,
        children_count=children_count,
        created_at=kp.created_at,
    )


@router.get("/", response_model=list[KnowledgePointResponse])
def list_knowledge_points(
    parent_id: int | None = Query(None, description="Filter by parent KP ID"),
    search: str | None = Query(None, description="Search by name or full_path"),
    depth: int | None = Query(None, description="Filter by depth level"),
    db: Session = Depends(get_db),
):
    """List knowledge points with optional filters."""
    query = db.query(KnowledgePoint)

    if parent_id is not None:
        query = query.filter(KnowledgePoint.parent_id == parent_id)
    if depth is not None:
        query = query.filter(KnowledgePoint.depth == depth)
    if search:
        like_pattern = f"%{search}%"
        query = query.filter(
            (KnowledgePoint.name.ilike(like_pattern))
            | (KnowledgePoint.full_path.ilike(like_pattern))
        )

    kps = query.order_by(KnowledgePoint.full_path).all()
    return [_kp_to_response(kp) for kp in kps]


@router.get("/tree", response_model=list[KnowledgePointTreeResponse])
def get_knowledge_point_tree(db: Session = Depends(get_db)):
    """Get the full knowledge point hierarchy as a nested tree."""
    # Get all root nodes (depth=0)
    roots = (
        db.query(KnowledgePoint)
        .filter(KnowledgePoint.depth == 0)
        .order_by(KnowledgePoint.name)
        .all()
    )

    def build_tree(kp: KnowledgePoint) -> KnowledgePointTreeResponse:
        children = sorted(kp.children, key=lambda c: c.name) if kp.children else []
        return KnowledgePointTreeResponse(
            id=kp.id,
            name=kp.name,
            full_path=kp.full_path,
            depth=kp.depth,
            description=kp.description,
            children=[build_tree(child) for child in children],
        )

    return [build_tree(root) for root in roots]


@router.get("/{kp_id}", response_model=KnowledgePointResponse)
def get_knowledge_point(kp_id: int, db: Session = Depends(get_db)):
    """Get a single knowledge point by ID."""
    kp = db.query(KnowledgePoint).filter(KnowledgePoint.id == kp_id).first()
    if not kp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge point not found")
    return _kp_to_response(kp)


@router.get("/{kp_id}/children", response_model=list[KnowledgePointResponse])
def get_children(kp_id: int, db: Session = Depends(get_db)):
    """Get immediate children of a knowledge point."""
    kp = db.query(KnowledgePoint).filter(KnowledgePoint.id == kp_id).first()
    if not kp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge point not found")

    children = (
        db.query(KnowledgePoint)
        .filter(KnowledgePoint.parent_id == kp_id)
        .order_by(KnowledgePoint.name)
        .all()
    )
    return [_kp_to_response(child) for child in children]


@router.post("/", response_model=KnowledgePointResponse, status_code=status.HTTP_201_CREATED)
def create_knowledge_point(
    body: KnowledgePointCreate,
    db: Session = Depends(get_db),
):
    """Create a new knowledge point."""
    # Determine depth and full_path
    depth = 0
    full_path = body.name

    if body.parent_id is not None:
        parent = db.query(KnowledgePoint).filter(KnowledgePoint.id == body.parent_id).first()
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Parent knowledge point not found",
            )
        depth = parent.depth + 1
        full_path = f"{parent.full_path} > {body.name}"

    # Check uniqueness of full_path
    existing = db.query(KnowledgePoint).filter_by(full_path=full_path).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Knowledge point with path '{full_path}' already exists",
        )

    kp = KnowledgePoint(
        name=body.name,
        parent_id=body.parent_id,
        depth=depth,
        full_path=full_path,
        description=body.description,
        importance=body.importance,
        prerequisite_ids=body.prerequisite_ids,
    )
    db.add(kp)
    db.commit()
    db.refresh(kp)
    return _kp_to_response(kp)


@router.post("/seed", response_model=SeedResponse)
def seed_knowledge_points(db: Session = Depends(get_db)):
    """Seed the database with the default math knowledge point taxonomy.

    Idempotent: re-running skips already-existing entries.
    """
    result = seed_taxonomy(db)
    return SeedResponse(**result)
