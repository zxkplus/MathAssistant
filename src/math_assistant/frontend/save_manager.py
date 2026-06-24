"""Frontend save manager — orchestrates question detection, turn recording,
and auto-save of .md / .html files for the Streamlit frontend.

Owns a SessionRecorder, a QuestionClassifier, and both exporters.  After each
agent response the save is triggered automatically — the user does not need
to click anything.
"""

from __future__ import annotations

from pathlib import Path

from math_assistant.config import OutputConfig
from math_assistant.session import (
    MarkdownExporter,
    HTMLExporter,
    SessionRecorder,
)
from math_assistant.frontend.question_classifier import QuestionClassifier


class FrontendSaveManager:
    """Orchestrates turn recording and auto-save for the Streamlit frontend.

    Usage per conversation::

        mgr = FrontendSaveManager(config.output)

        # Before each user message
        mgr.classify_and_start_group(user_message)
        mgr.recorder.start_turn(user_message)

        # During agent streaming
        mgr.recorder.add_assistant_text(chunk)
        mgr.recorder.record_tool_call(name, args)
        mgr.recorder.record_tool_result(name, output)

        # After agent completes
        turn = mgr.recorder.end_turn()
        mgr.recorder.add_turn_to_current_group(turn)
        mgr.save_current_group()

        # On "new conversation"
        mgr.reset()
    """

    def __init__(self, config: OutputConfig) -> None:
        self._recorder = SessionRecorder(
            model="",  # frontend doesn't expose model name to this layer
            image_dir=config.image_dir,
        )
        self._classifier = QuestionClassifier()
        self._md_exporter = MarkdownExporter(output_dir=config.save_dir)
        self._html_exporter = HTMLExporter(
            output_dir=config.save_dir,
            image_dir=config.image_dir,
            embed_images=config.embed_images,
        )
        self._do_html = config.html_export

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def recorder(self) -> SessionRecorder:
        """The underlying SessionRecorder (for feeding turn data)."""
        return self._recorder

    def classify_and_start_group(self, user_message: str) -> bool:
        """Classify the message and start a new question group if needed.

        Returns:
            True if a new group was created (this is a new question).
            False if the message is a follow-up to the existing group.
        """
        current_group = self._recorder.get_current_group()
        previous_topic = current_group.topic if current_group else None

        is_new = self._classifier.is_new_question(
            new_message=user_message,
            previous_question=previous_topic,
        )

        if is_new:
            self._recorder.start_question_group(topic=user_message)
            return True
        return False

    def save_current_group(self) -> tuple[Path | None, Path | None]:
        """Save the current question group to .md and .html.

        Returns:
            (md_path, html_path) — html_path is None if ``html_export`` is
            disabled.  Both are None if there is no current group or the save
            failed.
        """
        group = self._recorder.get_current_group()
        if group is None or not group.turns:
            return None, None

        session = self._recorder.session
        md_path: Path | None = None
        html_path: Path | None = None

        try:
            md_path = self._md_exporter.export_question_group(
                group, session, overwrite=True,
            )
        except Exception:
            pass  # best-effort; do not break the UI

        if self._do_html:
            try:
                html_path = self._html_exporter.export_question_group(
                    group, session, overwrite=True,
                )
            except Exception:
                pass

        return md_path, html_path

    def reset(self) -> None:
        """Reset state for a brand-new conversation."""
        self._recorder.new_session()
