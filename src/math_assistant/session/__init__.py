"""Session recording and multi-format export for MathAssistant.

Provides:
- SessionRecorder: tracks conversation turns in-memory
- MarkdownExporter: exports sessions as .md files with YAML frontmatter
- HTMLExporter: exports self-contained .html with KaTeX + base64 images
"""

from .recorder import Session, Turn, SessionRecorder
from .exporter import MarkdownExporter, HTMLExporter

__all__ = [
    "Session",
    "Turn",
    "SessionRecorder",
    "MarkdownExporter",
    "HTMLExporter",
]
