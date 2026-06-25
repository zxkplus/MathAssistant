"""Conversation turn recording and session state management.

Tracks every Q&A turn including assistant text, tool calls, tool results,
and generated images. The SessionRecorder is a mutable accumulator that
the REPL loop feeds as the agent streams, then finalizes each turn.
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class ToolCallRecord:
    """Record of a single tool invocation during a turn."""

    name: str
    input_args: dict[str, Any]
    output: str = ""
    error: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "input_args": self.input_args,
            "output": self.output,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ToolCallRecord":
        return cls(
            name=data["name"],
            input_args=data.get("input_args", {}),
            output=data.get("output", ""),
            error=data.get("error", False),
        )


@dataclass
class Turn:
    """A single Q&A turn: one user question and the assistant's full response."""

    question: str
    answer: str = ""
    tool_calls: list[ToolCallRecord] = field(default_factory=list)
    images: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    question_number: int = 0

    @property
    def has_tools(self) -> bool:
        return len(self.tool_calls) > 0

    @property
    def has_images(self) -> bool:
        return len(self.images) > 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "answer": self.answer,
            "question_number": self.question_number,
            "timestamp": self.timestamp.isoformat(),
            "tool_calls": [tc.to_dict() for tc in self.tool_calls],
            "images": self.images,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Turn":
        return cls(
            question=data["question"],
            answer=data.get("answer", ""),
            question_number=data.get("question_number", 0),
            timestamp=datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else datetime.now(),
            tool_calls=[ToolCallRecord.from_dict(tc) for tc in data.get("tool_calls", [])],
            images=data.get("images", []),
        )


@dataclass
class QuestionGroup:
    """Turns grouped by a single math problem (including follow-ups)."""

    group_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    topic: str = ""  # first question text, used for slug generation
    turns: list[Turn] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    @property
    def title(self) -> str:
        """Derive a title from the first question."""
        if self.topic.strip():
            q = self.topic.strip()
            return q[:80] + ("…" if len(q) > 80 else "")
        if self.turns:
            q = self.turns[0].question.strip()
            return q[:80] + ("…" if len(q) > 80 else "")
        return "MathAssistant Question"

    def to_dict(self, turn_index_map: dict[int, int] | None = None) -> dict[str, Any]:
        """Serialize to dict. If *turn_index_map* is provided, it maps
        ``id(turn)`` → index in the session's turn list; the group stores
        turn indices instead of full turn dicts."""
        turns_data: list[int] | list[dict]
        if turn_index_map is not None:
            turns_data = [turn_index_map[id(t)] for t in self.turns if id(t) in turn_index_map]
        else:
            turns_data = [t.to_dict() for t in self.turns]
        return {
            "group_id": self.group_id,
            "topic": self.topic,
            "turns": turns_data,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any], turns: list[Turn] | None = None) -> "QuestionGroup":
        """Deserialize. If *turns* is provided and the stored turns are
        integer indices, resolve indices against that list."""
        raw_turns = data.get("turns", [])
        resolved: list[Turn] = []
        if raw_turns and isinstance(raw_turns[0], int) and turns is not None:
            resolved = [turns[i] for i in raw_turns if 0 <= i < len(turns)]
        elif raw_turns and isinstance(raw_turns[0], dict):
            resolved = [Turn.from_dict(t) for t in raw_turns]
        return cls(
            group_id=data.get("group_id", ""),
            topic=data.get("topic", ""),
            turns=resolved,
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now(),
        )


@dataclass
class Session:
    """A complete conversation session with metadata."""

    session_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    model: str = ""
    turns: list[Turn] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    question_groups: list[QuestionGroup] = field(default_factory=list)

    @property
    def question_count(self) -> int:
        return len(self.turns)

    @property
    def all_images(self) -> list[str]:
        """All unique images across all turns."""
        seen = set()
        result = []
        for turn in self.turns:
            for img in turn.images:
                if img not in seen:
                    seen.add(img)
                    result.append(img)
        return result

    @property
    def title(self) -> str:
        """Derive a title from the first question."""
        if self.turns:
            q = self.turns[0].question.strip()
            return q[:80] + ("…" if len(q) > 80 else "")
        return "MathAssistant Session"

    def to_dict(self) -> dict[str, Any]:
        # Build turn index map for compact group serialization
        turn_index_map = {id(t): i for i, t in enumerate(self.turns)}
        return {
            "version": 1,
            "session_id": self.session_id,
            "model": self.model,
            "created_at": self.created_at.isoformat(),
            "title": self.title,
            "question_count": self.question_count,
            "turns": [t.to_dict() for t in self.turns],
            "question_groups": [
                g.to_dict(turn_index_map=turn_index_map)
                for g in self.question_groups
            ],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Session":
        turns = [Turn.from_dict(t) for t in data.get("turns", [])]
        groups = [
            QuestionGroup.from_dict(g, turns=turns)
            for g in data.get("question_groups", [])
        ]
        return cls(
            session_id=data.get("session_id", ""),
            model=data.get("model", ""),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            turns=turns,
            question_groups=groups,
        )


class SessionRecorder:
    """Mutable accumulator that tracks a conversation as it streams.

    Usage in the REPL loop::

        recorder = SessionRecorder(model="deepseek-chat", image_dir="./images")

        recorder.start_turn("Solve x^2 - 5x + 6 = 0")
        recorder.add_assistant_text("Let me solve this...")
        recorder.add_tool_call("execute_python", {"code": "..."})
        recorder.add_tool_result("execute_python", "[2, 3]")
        recorder.end_turn()
    """

    # Patterns for detecting image paths in tool output
    IMAGE_PATTERN = re.compile(
        r'(?:images?/[\w\-./]+\.(?:png|jpg|jpeg|svg|gif|webp))',
        re.IGNORECASE,
    )

    def __init__(self, model: str = "", image_dir: str = "./images"):
        self._session = Session(model=model)
        self._image_dir = Path(image_dir)
        self._current_turn: Turn | None = None
        self._text_parts: list[str] = []
        self._pending_tool_calls: list[ToolCallRecord] = []
        self._current_group: QuestionGroup | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def session(self) -> Session:
        return self._session

    def start_turn(self, question: str) -> None:
        """Begin a new Q&A turn."""
        self._current_turn = None
        self._text_parts = []
        self._pending_tool_calls = []

        self._current_turn = Turn(
            question=question,
            question_number=self._session.question_count + 1,
        )

    def add_assistant_text(self, text: str) -> None:
        """Accumulate assistant text (may be called multiple times during streaming)."""
        if text and text.strip():
            self._text_parts.append(text)

    def record_tool_call(self, name: str, args: dict[str, Any]) -> None:
        """Record that the agent has requested a tool call."""
        record = ToolCallRecord(name=name, input_args=args)
        self._pending_tool_calls.append(record)

    def record_tool_result(self, name: str, output: str) -> None:
        """Record a tool's execution result.

        Matches against pending tool calls by name (FIFO) and also scans
        the output for generated image paths.
        """
        # Attach result to the first pending tool call with matching name
        for tc in self._pending_tool_calls:
            if tc.name == name and not tc.output:
                tc.output = output
                tc.error = "Error" in output or "Traceback" in output
                break

    def end_turn(self) -> Turn:
        """Finalize the current turn: join text, collect images, add to session.

        Returns the completed Turn.
        """
        if self._current_turn is None:
            raise RuntimeError("end_turn() called without start_turn()")

        turn = self._current_turn

        # Join accumulated text
        turn.answer = "\n\n".join(self._text_parts)

        # Move tool calls into the turn (only those that actually ran)
        turn.tool_calls = [tc for tc in self._pending_tool_calls if tc.output]

        # Extract images from tool outputs
        turn.images = self._extract_images(turn)

        # Store in session
        self._session.turns.append(turn)

        # Reset state
        self._current_turn = None
        self._text_parts = []
        self._pending_tool_calls = []

        return turn

    # ------------------------------------------------------------------
    # Image detection
    # ------------------------------------------------------------------

    def _extract_images(self, turn: Turn) -> list[str]:
        """Find all image paths referenced in tool outputs."""
        images: list[str] = []
        seen: set[str] = set()

        for tc in turn.tool_calls:
            for match in self.IMAGE_PATTERN.finditer(tc.output):
                path = match.group(0)
                if path not in seen:
                    seen.add(path)
                    images.append(path)

        return images

    # ------------------------------------------------------------------
    # Question groups
    # ------------------------------------------------------------------

    def start_question_group(self, topic: str) -> str:
        """Begin a new question group. Returns the group_id."""
        group = QuestionGroup(topic=topic)
        self._current_group = group
        self._session.question_groups.append(group)
        return group.group_id

    def add_turn_to_current_group(self, turn: Turn) -> None:
        """Add a completed turn to the current question group."""
        if self._current_group is not None:
            self._current_group.turns.append(turn)
            self._current_group.updated_at = datetime.now()

    def get_current_group(self) -> QuestionGroup | None:
        """Return the current question group, or None."""
        return self._current_group

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def new_session(self) -> None:
        """Reset for a brand-new conversation."""
        self._session = Session(model=self._session.model)
        self._current_turn = None
        self._text_parts = []
        self._pending_tool_calls = []
        self._current_group = None


# ---------------------------------------------------------------------------
# Top-level JSON serialization helpers
# ---------------------------------------------------------------------------

def serialize_session(session: Session, path: Path) -> None:
    """Write a Session to a JSON file.

    Args:
        session: The session to serialize.
        path: File path to write (e.g. ``workspace/session.json``).
    """
    data = session.to_dict()
    path.parent.mkdir(parents=True, exist_ok=True)
    # Atomic write: temp file then rename
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    tmp_path.replace(path)


def deserialize_session(path: Path) -> Session:
    """Read a Session from a JSON file.

    Args:
        path: Path to a ``session.json`` file.

    Returns:
        A reconstructed Session object.
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return Session.from_dict(data)
