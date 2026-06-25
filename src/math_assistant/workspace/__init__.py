"""Workspace-based session management for MathAssistant.

Each session gets a self-contained directory under ``workspace_root``:
  {date}-{id8}-{slug}/
    session.json   — full structured session data
    session.md     — Markdown export
    session.html   — self-contained HTML export
    images/        — all images scoped to this session
"""

from .manager import WorkspaceManager, WorkspaceContext
from .index import WorkspaceIndex

__all__ = [
    "WorkspaceManager",
    "WorkspaceContext",
    "WorkspaceIndex",
]
