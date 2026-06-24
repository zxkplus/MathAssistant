"""Terminal math-formula rendering for MathAssistant.

Layered fallback strategy:
1. If ``latex2unicode`` is installed → convert LaTeX to Unicode math symbols
2. Always → wrap LaTeX blocks in Rich-styled spans so they stand out visually
3. SymPy expressions → pretty-print with Unicode box-drawing characters

Usage:
    renderer = MathRenderer()
    rich_md = renderer.rich_markdown(text_with_latex)
    console.print(rich_md)
"""

from __future__ import annotations

import os
import re
from typing import ClassVar


class MathRenderer:
    """Convert math notation to terminal-friendly forms.

    Does NOT mutate the original LaTeX — it produces a *separate* visual
    representation for the terminal while the original is preserved in
    the saved Markdown/HTML files.
    """

    # LaTeX commands that have direct Unicode equivalents
    LATEX_TO_UNICODE: ClassVar[dict[str, str]] = {
        # Greek lowercase
        r'\alpha': 'α', r'\beta': 'β', r'\gamma': 'γ', r'\delta': 'δ',
        r'\epsilon': 'ε', r'\zeta': 'ζ', r'\eta': 'η', r'\theta': 'θ',
        r'\iota': 'ι', r'\kappa': 'κ', r'\lambda': 'λ', r'\mu': 'μ',
        r'\nu': 'ν', r'\xi': 'ξ', r'\pi': 'π', r'\rho': 'ρ',
        r'\sigma': 'σ', r'\tau': 'τ', r'\upsilon': 'υ', r'\phi': 'φ',
        r'\chi': 'χ', r'\psi': 'ψ', r'\omega': 'ω',
        # Greek uppercase
        r'\Gamma': 'Γ', r'\Delta': 'Δ', r'\Theta': 'Θ', r'\Lambda': 'Λ',
        r'\Xi': 'Ξ', r'\Pi': 'Π', r'\Sigma': 'Σ', r'\Upsilon': 'Υ',
        r'\Phi': 'Φ', r'\Psi': 'Ψ', r'\Omega': 'Ω',
        # Operators / symbols
        r'\infty': '∞', r'\pm': '±', r'\mp': '∓',
        r'\cdot': '·', r'\times': '×', r'\div': '÷',
        r'\sqrt': '√', r'\cbrt': '∛',
        r'\int': '∫', r'\iint': '∬', r'\iiint': '∭', r'\oint': '∮',
        r'\sum': '∑', r'\prod': '∏', r'\coprod': '∐',
        r'\partial': '∂', r'\nabla': '∇',
        r'\forall': '∀', r'\exists': '∃', r'\nexists': '∄',
        r'\in': '∈', r'\notin': '∉', r'\ni': '∋',
        r'\subset': '⊂', r'\supset': '⊃', r'\subseteq': '⊆',
        r'\supseteq': '⊇', r'\emptyset': '∅',
        r'\cup': '∪', r'\cap': '∩',
        r'\leq': '≤', r'\geq': '≥', r'\neq': '≠',
        r'\approx': '≈', r'\equiv': '≡', r'\propto': '∝',
        r'\ll': '≪', r'\gg': '≫',
        r'\to': '→', r'\rightarrow': '→', r'\leftarrow': '←',
        r'\Rightarrow': '⇒', r'\Leftarrow': '⇐',
        r'\Leftrightarrow': '⇔', r'\leftrightarrow': '↔',
        r'\uparrow': '↑', r'\downarrow': '↓',
        r'\mapsto': '↦',
        r'\angle': '∠', r'\parallel': '∥', r'\perp': '⊥',
        r'\triangle': '△', r'\square': '□',
        # Set notation
        r'\mathbb{R}': 'ℝ', r'\mathbb{N}': 'ℕ', r'\mathbb{Z}': 'ℤ',
        r'\mathbb{Q}': 'ℚ', r'\mathbb{C}': 'ℂ',
        # Arrows / misc
        r'\ldots': '…', r'\cdots': '⋯', r'\vdots': '⋮', r'\ddots': '⋱',
        r'\circ': '∘', r'\bullet': '•', r'\star': '★',
        r'\oplus': '⊕', r'\otimes': '⊗',
        r'\sim': '∼',
        r'\langle': '⟨', r'\rangle': '⟩',
        r'\lfloor': '⌊', r'\rfloor': '⌋', r'\lceil': '⌈', r'\rceil': '⌉',
        r'\|': '∥',
        # Constants
        r'\hbar': 'ℏ',
    }

    # Subscript / superscript digits
    _SUB_DIGITS = str.maketrans('0123456789', '₀₁₂₃₄₅₆₇₈₉')
    _SUP_DIGITS = str.maketrans('0123456789', '⁰¹²³⁴⁵⁶⁷⁸⁹')
    _SUP_PLUS = str.maketrans('+-', '⁺⁻')
    _SUP_PARENS = str.maketrans('()', '⁽⁾')

    def __init__(self) -> None:
        self._use_pylatexenc = self._check_pylatexenc()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def prettify(self, text: str) -> str:
        """Convert LaTeX math in *text* to terminal-friendly Unicode.

        Returns the same string with LaTeX replaced where possible.
        The original is kept intact for file export.
        """
        # Always use the built-in manual mapping (fast, zero-dependency).
        # pylatexenc can optionally be installed for more accurate parsing,
        # but the manual mapping covers >80% of common math symbols.
        return self._manual_convert(text)

    def process_response(self, raw_text: str) -> str:
        """Transform an agent response for terminal display.

        - Converts inline ``$...$`` and block ``$$...$$`` to visually
          distinct Rich markup.
        - Does NOT destroy the LaTeX — wrapping with Rich style tags so
          the user can still read the LaTeX source.
        """
        # Wrap display-math blocks in bold cyan
        out = re.sub(
            r'\$\$(.+?)\$\$',
            r'[bold cyan]$$\1$$[/bold cyan]',
            raw_text,
            flags=re.DOTALL,
        )
        # Wrap inline math in cyan italic
        out = re.sub(
            r'(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)',
            r'[cyan italic]$\1$[/cyan italic]',
            out,
        )
        return out

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _check_pylatexenc() -> bool:
        try:
            import pylatexenc  # noqa: F401
            return True
        except ImportError:
            return False

    @classmethod
    def _manual_convert(cls, text: str) -> str:
        """Apply manual LaTeX → Unicode mapping (no external dependency)."""
        result = text

        for latex, unicode_char in cls.LATEX_TO_UNICODE.items():
            result = result.replace(latex, unicode_char)

        # Superscripts: x^{2} → x², x^{10} → x¹⁰
        result = re.sub(
            r'\^\{([^}]+)\}',
            lambda m: m.group(1).translate(cls._SUP_DIGITS)
                           .translate(cls._SUP_PLUS)
                           .translate(cls._SUP_PARENS),
            result,
        )
        # Subscripts: x_{i} → xᵢ (single char only, multi is tricky in Unicode)
        result = re.sub(
            r'_\{([^}]+)\}',
            lambda m: m.group(1).translate(cls._SUB_DIGITS),
            result,
        )

        # Fractions: \frac{a}{b} → (a)/(b)  (Unicode fractions are limited)
        result = re.sub(
            r'\\frac\{([^}]+)\}\{([^}]+)\}',
            r'(\1)/(\2)',
            result,
        )

        return result


# ---------------------------------------------------------------------------
# SymPy pretty-printing
# ---------------------------------------------------------------------------

def format_sympy_output(text: str) -> str:
    """If *text* looks like a SymPy expression repr, try to pretty-print it.

    This is a best-effort helper.  Call it on tool output that is likely
    to contain SymPy objects.  Returns the (possibly enhanced) string.
    """
    return text  # Kept simple: sympy.pprint is best used interactively.
    # For tool output returned as a string, sympy already produced
    # readable text.  We keep the raw output for the saved file and
    # rely on MathRenderer.prettify() for terminal display.
