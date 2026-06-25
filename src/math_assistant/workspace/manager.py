"""Workspace manager — creates and manages per-session workspace directories.

Each session gets a self-contained directory under ``workspace_root``::

    {date}-{id8}-{slug}/
        session.json
        session.md
        session.html
        images/
"""

from __future__ import annotations

import shutil
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .index import WorkspaceIndex


# ---------------------------------------------------------------------------
# WorkspaceContext — immutable value object with all paths for one session
# ---------------------------------------------------------------------------

@dataclass
class WorkspaceContext:
    """Immutable value object holding all filesystem paths for one session."""

    session_id: str
    dir_name: str              # e.g. "20260625-abc12345-solving-quadratic"
    workspace_dir: Path        # full path to the session directory
    images_dir: Path           # workspace_dir / "images"
    session_json_path: Path    # workspace_dir / "session.json"
    session_md_path: Path      # workspace_dir / "session.md"
    session_html_path: Path    # workspace_dir / "session.html"

    def ensure_dirs(self) -> None:
        """Create the workspace directory and images/ subdirectory."""
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.images_dir.mkdir(parents=True, exist_ok=True)

    def delete(self) -> None:
        """Remove the entire workspace directory tree."""
        if self.workspace_dir.exists():
            shutil.rmtree(self.workspace_dir)

    def image_path(self, filename: str) -> Path:
        """Resolve an image filename relative to the images_dir."""
        return self.images_dir / filename

    def exists(self) -> bool:
        """Check if the workspace directory exists on disk."""
        return self.workspace_dir.is_dir()


# ---------------------------------------------------------------------------
# WorkspaceManager
# ---------------------------------------------------------------------------

class WorkspaceManager:
    """Creates, lists, and deletes per-session workspace directories.

    Usage::

        mgr = WorkspaceManager("./workspaces")
        ctx = mgr.create_workspace(model="deepseek-chat")
        # ... use ctx.images_dir, ctx.session_json_path, etc.
        mgr.finalize_workspace(ctx, session)  # writes index entry
    """

    def __init__(self, workspace_root: str | Path) -> None:
        self._root = Path(workspace_root)
        self._root.mkdir(parents=True, exist_ok=True)
        self._index = WorkspaceIndex(self._root)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def root(self) -> Path:
        """The workspace root directory."""
        return self._root

    @property
    def index(self) -> WorkspaceIndex:
        """The underlying WorkspaceIndex for querying."""
        return self._index

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    def create_workspace(
        self,
        session_id: str | None = None,
        slug: str = "",
        model: str = "",
        created_at: datetime | None = None,
    ) -> WorkspaceContext:
        """Create a new workspace directory and return its context.

        Args:
            session_id: 8-char hex id. Auto-generated if None.
            slug: Human-readable label for the directory name.
            model: Model name (stored in metadata, not in the path).
            created_at: Timestamp. Defaults to now.

        Returns:
            WorkspaceContext with all paths resolved.
        """
        sid = session_id or str(uuid.uuid4())[:8]
        ts = created_at or datetime.now()
        date_str = ts.strftime("%Y%m%d")
        safe_slug = _slugify(slug) if slug else "math"

        dir_name = f"{date_str}-{sid}-{safe_slug}"
        ws_dir = self._root / dir_name

        ctx = WorkspaceContext(
            session_id=sid,
            dir_name=dir_name,
            workspace_dir=ws_dir,
            images_dir=ws_dir / "images",
            session_json_path=ws_dir / "session.json",
            session_md_path=ws_dir / "session.md",
            session_html_path=ws_dir / "session.html",
        )
        ctx.ensure_dirs()
        return ctx

    def get_workspace(self, session_id: str) -> WorkspaceContext | None:
        """Look up an existing workspace by session_id from the index."""
        entry = self._index.find_by_id(session_id)
        if entry is None:
            return None
        return self._ctx_from_entry(entry)

    def list_workspaces(self, limit: int = 50) -> list[WorkspaceContext]:
        """Return workspace contexts for all known sessions (newest first)."""
        entries = self._index.list_all(limit=limit)
        return [self._ctx_from_entry(e) for e in entries]

    def finalize_workspace(self, ctx: WorkspaceContext, session: object) -> None:
        """Write/update the index entry for a workspace.

        Call this after session.json has been written so the index
        can read metadata from it.

        Args:
            ctx: The workspace context.
            session: A Session object (used for title, model, question_count).
                     Alternatively, any object with .title, .model, .question_count.
        """
        entry = {
            "id": ctx.session_id,
            "slug": ctx.dir_name.split("-", 2)[-1] if "-" in ctx.dir_name else "math",
            "dir_name": ctx.dir_name,
            "title": getattr(session, "title", "MathAssistant Session"),
            "model": getattr(session, "model", ""),
            "question_count": getattr(session, "question_count", 0),
            "created_at": getattr(session, "created_at", datetime.now()).isoformat() if hasattr(getattr(session, "created_at", None), "isoformat") else str(getattr(session, "created_at", "")),
            "updated_at": datetime.now().isoformat(),
        }
        self._index.add_session(entry)

    def delete_workspace(self, session_id: str) -> bool:
        """Delete a workspace directory and remove it from the index.

        Returns True if the workspace was found and deleted.
        """
        entry = self._index.find_by_id(session_id)
        if entry is None:
            return False

        dir_name = entry.get("dir_name", "")
        ws_dir = self._root / dir_name if dir_name else None

        # Remove from index first
        self._index.remove_session(session_id)

        # Then delete the directory
        if ws_dir and ws_dir.exists():
            shutil.rmtree(ws_dir)

        return True

    def rebuild_index(self) -> int:
        """Rebuild the index from a directory scan. Returns entry count."""
        return self._index.rebuild()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _ctx_from_entry(self, entry: dict) -> WorkspaceContext:
        """Reconstruct a WorkspaceContext from an index entry."""
        dir_name = entry.get("dir_name", "")
        ws_dir = self._root / dir_name
        return WorkspaceContext(
            session_id=entry.get("id", ""),
            dir_name=dir_name,
            workspace_dir=ws_dir,
            images_dir=ws_dir / "images",
            session_json_path=ws_dir / "session.json",
            session_md_path=ws_dir / "session.md",
            session_html_path=ws_dir / "session.html",
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _slugify(text: str) -> str:
    """Convert arbitrary text to a safe filename slug (ASCII only)."""
    import re
    slug = text.lower().strip()
    # Transliterate common CJK characters? No — just strip them.
    # Keep only ASCII word chars, dashes, spaces.
    slug = re.sub(r'[^\w\s-]', '', slug, flags=re.ASCII)
    slug = re.sub(r'[-\s]+', '-', slug)
    return slug.strip('-')[:60] or "math"
