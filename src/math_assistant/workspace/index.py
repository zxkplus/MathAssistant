"""Workspace index — a JSON file cataloguing all session workspaces.

The index is a speed layer / cache. The source of truth is the workspace
directory names themselves (``{date}-{id8}-{slug}``), so the index can
always be rebuilt by scanning.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any


# Regex to parse directory names: YYYYMMDD-id-slug
_DIR_RE = re.compile(r"^(\d{8})-([0-9a-f]{8})-(.+)$")


class WorkspaceIndex:
    """Thread-safe reader/writer for ``workspaces/index.json``.

    Uses atomic writes (temp file + rename) and advisory file locks
    to guard against concurrent-process corruption.
    """

    def __init__(self, workspace_root: Path) -> None:
        self._root = Path(workspace_root)
        self._path = self._root / "index.json"
        self._data: dict[str, Any] | None = None   # lazy-loaded

    # ------------------------------------------------------------------
    # Read API
    # ------------------------------------------------------------------

    @property
    def sessions(self) -> list[dict[str, Any]]:
        """Return all session entries (most recent first)."""
        return list(self._load().get("sessions", []))

    def find_by_id(self, session_id: str) -> dict[str, Any] | None:
        """Find a session entry by its session_id."""
        for entry in self.sessions:
            if entry.get("id") == session_id:
                return entry
        return None

    def find_by_date(self, date_str: str) -> list[dict[str, Any]]:
        """Find session entries for a specific date (YYYYMMDD)."""
        return [
            e for e in self.sessions
            if e.get("dir_name", "").startswith(date_str)
        ]

    def list_all(self, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        """Return a slice of the session list."""
        sessions = self.sessions
        return sessions[offset:offset + limit]

    # ------------------------------------------------------------------
    # Write API
    # ------------------------------------------------------------------

    def add_session(self, entry: dict[str, Any]) -> None:
        """Add or update a session entry (matched by ``id``)."""
        data = self._load()
        sessions = data.get("sessions", [])

        # Replace existing or prepend new (newest first)
        entry_id = entry.get("id")
        replaced = False
        for i, s in enumerate(sessions):
            if s.get("id") == entry_id:
                sessions[i] = entry
                replaced = True
                break
        if not replaced:
            sessions.insert(0, entry)

        data["sessions"] = sessions
        data["updated"] = datetime.now().isoformat()
        self._save(data)

    def remove_session(self, session_id: str) -> bool:
        """Remove a session entry by id. Returns True if removed."""
        data = self._load()
        sessions = data.get("sessions", [])
        new_list = [s for s in sessions if s.get("id") != session_id]
        if len(new_list) == len(sessions):
            return False
        data["sessions"] = new_list
        data["updated"] = datetime.now().isoformat()
        self._save(data)
        return True

    def rebuild(self) -> int:
        """Rebuild the index from directory scan. Returns entry count.

        Use this to recover from a corrupted or missing index.json.
        """
        self._root.mkdir(parents=True, exist_ok=True)
        entries: list[dict[str, Any]] = []

        for child in sorted(self._root.iterdir(), reverse=True):
            if not child.is_dir():
                continue
            m = _DIR_RE.match(child.name)
            if not m:
                continue
            date_str, sid, slug = m.groups()
            session_json = child / "session.json"
            meta = _read_session_meta(session_json, sid, slug, date_str)
            entries.append(meta)

        data = {
            "version": 1,
            "updated": datetime.now().isoformat(),
            "sessions": entries,
        }
        self._save(data)
        return len(entries)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _load(self) -> dict[str, Any]:
        """Load index from disk (lazy, cached)."""
        if self._data is not None:
            return self._data

        self._root.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            # First run: build from scan
            self._data = {"version": 1, "sessions": [], "updated": ""}
            self.rebuild()
            return self._data

        try:
            with open(self._path, "r", encoding="utf-8") as f:
                self._data = json.load(f)
        except (json.JSONDecodeError, OSError):
            # Corrupted — rebuild
            self._data = {"version": 1, "sessions": [], "updated": ""}
            self.rebuild()
        return self._data

    def _save(self, data: dict[str, Any]) -> None:
        """Atomically write index data to disk."""
        self._root.mkdir(parents=True, exist_ok=True)
        tmp_path = self._path.with_suffix(".tmp")

        # Advisory lock (cross-platform)
        with _file_lock(self._path):
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)

        tmp_path.replace(self._path)  # atomic on most OSes
        self._data = data


def _read_session_meta(
    session_json: Path,
    sid: str,
    slug: str,
    date_str: str,
) -> dict[str, Any]:
    """Extract metadata from a session.json file for the index."""
    title = slug.replace("-", " ").title()
    model = ""
    question_count = 0
    created_at = ""
    updated_at = ""

    if session_json.exists():
        try:
            with open(session_json, "r", encoding="utf-8") as f:
                data = json.load(f)
            title = data.get("title", title)
            model = data.get("model", "")
            question_count = data.get("question_count", 0)
            created_at = data.get("created_at", "")
            # Use the file mtime for updated_at if not in the json
            updated_at = created_at
        except (json.JSONDecodeError, OSError):
            pass

    return {
        "id": sid,
        "slug": slug,
        "dir_name": f"{date_str}-{sid}-{slug}",
        "title": title,
        "model": model,
        "question_count": question_count,
        "created_at": created_at,
        "updated_at": updated_at,
    }


# -----------------------------------------------------------------------
# Cross-platform advisory file lock
# -----------------------------------------------------------------------

class _file_lock:
    """Minimal cross-platform file lock context manager."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._lockfile = path.with_suffix(path.suffix + ".lock")
        self._fd: int | None = None

    def __enter__(self) -> "_file_lock":
        self._lockfile.parent.mkdir(parents=True, exist_ok=True)
        self._fd = os.open(str(self._lockfile), os.O_CREAT | os.O_RDWR)
        if sys.platform == "win32":
            import msvcrt
            msvcrt.locking(self._fd, msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(self._fd, fcntl.LOCK_EX)
        return self

    def __exit__(self, *args: Any) -> None:
        if self._fd is not None:
            if sys.platform == "win32":
                import msvcrt
                try:
                    msvcrt.locking(self._fd, msvcrt.LK_UNLCK, 1)
                except Exception:
                    pass
            else:
                import fcntl
                try:
                    fcntl.flock(self._fd, fcntl.LOCK_UN)
                except Exception:
                    pass
            os.close(self._fd)
            self._fd = None
        try:
            self._lockfile.unlink(missing_ok=True)
        except Exception:
            pass
