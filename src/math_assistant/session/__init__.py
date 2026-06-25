"""Session recording and multi-format export for MathAssistant.

Provides:
- SessionRecorder: tracks conversation turns in-memory
- MarkdownExporter: exports sessions as .md files with YAML frontmatter
- HTMLExporter: exports self-contained .html with KaTeX + base64 images
- serialize_session / deserialize_session: JSON persistence
"""

from .recorder import (
    QuestionGroup,
    Session,
    Turn,
    ToolCallRecord,
    SessionRecorder,
    serialize_session,
    deserialize_session,
)
from .exporter import MarkdownExporter, HTMLExporter

__all__ = [
    "QuestionGroup",
    "Session",
    "Turn",
    "ToolCallRecord",
    "SessionRecorder",
    "MarkdownExporter",
    "HTMLExporter",
    "serialize_session",
    "deserialize_session",
]
