"""Question classifier — determines whether a new user message is a follow-up
to the current math problem or a brand-new question.

Uses pure heuristics (no LLM calls, zero latency) so that auto-save decisions
happen instantly.  The classifier API is intentionally simple so that an
LLM-based implementation can be swapped in later via the same interface.
"""

from __future__ import annotations

import re
from typing import Optional


# ── Pattern sets ────────────────────────────────────────────────────────────

# Phrases that strongly indicate the user wants a NEW / different problem.
_EXPLICIT_NEW_MARKERS = [
    "new problem", "different problem", "different question",
    "next problem", "next question", "another problem", "another question",
    "let's switch", "switch to", "change topic", "change the topic",
    "new topic", "move on", "moving on",
    # Chinese variants
    "换一题", "新问题", "新的问题", "下一题", "换个问题",
    "换一个问题", "换题目", "下一个", "再来一题",
]

# Phrases that strongly indicate the user is asking a FOLLOW-UP.
_FOLLOW_UP_KEYWORDS = [
    # English
    "why", "explain", "elaborate", "clarify", "what about",
    "how about", "can you also", "could you also", "please also",
    "what if", "how do you", "how did you", "how does",
    "show me", "show the", "tell me", "step", "steps",
    "detail", "details", "more detail", "in detail",
    "based on that", "based on this", "using that", "using this",
    "with that", "with this", "then what", "and then",
    "what is the", "what's the", "what are",
    "can you explain", "could you explain",
    "i don't understand", "i do not understand",
    "i'm confused", "i am confused",
    "modify", "change it", "instead", "alternatively",
    "also", "additionally", "furthermore", "moreover",
    "continue", "go on", "extend", "expand",
    # Chinese
    "为什么", "解释", "详细", "步骤", "能再", "可以说",
    "能详细", "能具体", "能讲", "能说明",
    "不太懂", "没看懂", "没明白", "不理解",
    "接着", "继续", "然后", "还有", "另外",
    "用这个", "基于此", "在这个基础上",
    "修改", "改成", "换成", "换一种",
    "怎么", "如何", "怎么样",
]

# Math expression indicators — these suggest the message contains an
# equation or mathematical expression (likely a new problem, not a follow-up).
_MATH_EXPRESSION_PATTERNS = [
    r'\$',           # LaTeX inline math
    r'\\frac',       # fraction
    r'\\sum',        # sum
    r'\\int',        # integral
    r'\\lim',        # limit
    r'\\sqrt',       # square root
    r'\\alpha|\\beta|\\gamma|\\theta|\\pi',  # Greek letters
    r'\\sin|\\cos|\\tan|\\log|\\ln|\\exp',   # functions
    r'\^',           # exponent
    r'=',            # equation sign (weak signal alone)
    r'\\begin\{',    # LaTeX environment
    r'\\cdot|\\times|\\div',  # operators
    r'\\infty',      # infinity
]


class QuestionClassifier:
    """Heuristic classifier for "new question" vs "follow-up" detection.

    Usage::

        classifier = QuestionClassifier()
        is_new = classifier.is_new_question(
            new_message="Can you explain step 3?",
            previous_question="Solve x^2 + 2x + 1 = 0",
        )  # → False (it's a follow-up)
    """

    def is_new_question(
        self,
        new_message: str,
        previous_question: Optional[str] = None,
    ) -> bool:
        """Return True if *new_message* is a distinct new math problem.

        Args:
            new_message: The user's latest message.
            previous_question: The first question of the current group,
                or None if there is no active question group.

        Returns:
            True if this should start a new question group.
        """
        # No previous question → always new
        if previous_question is None:
            return True

        text = new_message.strip()
        if not text:
            return False  # empty messages shouldn't happen; treat as follow-up

        # ── Signal 1: Explicit new-problem markers ──
        if self._has_explicit_new_marker(text):
            return True

        # ── Signal 2: Follow-up keywords ──
        if self._has_follow_up_keywords(text):
            return False

        # ── Signal 3: Short message (≤ 12 words) without math expression ──
        word_count = self._word_count(text)
        has_math = self._has_math_expression(text)
        if word_count <= 12 and not has_math:
            return False  # likely a clarification or follow-up

        # ── Signal 4: Short message (≤ 15 words) WITH math expression ──
        if word_count <= 15 and has_math:
            return True  # likely a self-contained new math problem

        # ── Default ──
        # Longer messages: default to NEW (conservative — better to create
        # an extra file than to mix unrelated questions).
        return True

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _has_explicit_new_marker(text: str) -> bool:
        lower = text.lower()
        return any(marker in lower for marker in _EXPLICIT_NEW_MARKERS)

    @staticmethod
    def _has_follow_up_keywords(text: str) -> bool:
        lower = text.lower()
        return any(keyword in lower for keyword in _FOLLOW_UP_KEYWORDS)

    @staticmethod
    def _has_math_expression(text: str) -> bool:
        return any(
            re.search(pattern, text)
            for pattern in _MATH_EXPRESSION_PATTERNS
        )

    @staticmethod
    def _word_count(text: str) -> int:
        """Count words (CJK-aware: each CJK character counts as one word)."""
        # Count CJK characters individually
        cjk = sum(1 for ch in text if '一' <= ch <= '鿿')
        # Count space-separated tokens for the rest
        non_cjk = text
        for ch in text:
            if '一' <= ch <= '鿿':
                non_cjk = non_cjk.replace(ch, ' ')
        ascii_words = len(non_cjk.split())
        return cjk + ascii_words
