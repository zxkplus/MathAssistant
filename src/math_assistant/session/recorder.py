"""Conversation turn recording and session state management.

Tracks every Q&A turn including assistant text, tool calls, tool results,
and generated images. The SessionRecorder is a mutable accumulator that
the REPL loop feeds as the agent streams, then finalizes each turn.
"""

from __future__ import annotations

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


@dataclass
class Session:
    """A complete conversation session with metadata."""

    session_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    model: str = ""
    turns: list[Turn] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

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
    # Convenience
    # ------------------------------------------------------------------

    def new_session(self) -> None:
        """Reset for a brand-new conversation."""
        self._session = Session(model=self._session.model)
        self._current_turn = None
        self._text_parts = []
        self._pending_tool_calls = []
