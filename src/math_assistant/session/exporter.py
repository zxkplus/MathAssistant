"""Multi-format export for MathAssistant sessions.

Exports:
- Markdown (.md) with YAML frontmatter — git-friendly, great in VS Code / Typora
- Self-contained HTML (.html) — KaTeX math, base64 images, dark/light theme
"""

from __future__ import annotations

import base64
import json
import mimetypes
import textwrap
from datetime import datetime
from pathlib import Path
from typing import Optional

from .recorder import Session, Turn, ToolCallRecord


# ---------------------------------------------------------------------------
# Markdown Exporter
# ---------------------------------------------------------------------------

class MarkdownExporter:
    """Export a Session to a well-structured Markdown file.

    Features:
    - YAML frontmatter with metadata (title, date, session_id, model)
    - Each turn gets its own Q&A section
    - Tool calls folded inside <details> blocks
    - Images embedded as ``![caption](path/to/image.png)``
    - LaTeX kept as standard ``$...$`` / ``$$...$$`` for MathJax/KaTeX viewers
    """

    def __init__(self, output_dir: str = "./sessions") -> None:
        self.output_dir = Path(output_dir)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def export(self, session: Session) -> Path:
        """Export a session to a .md file.  Returns the output Path."""
        self.output_dir.mkdir(parents=True, exist_ok=True)

        filename = self._filename(session)
        path = self.output_dir / filename

        content = self._render(session)
        path.write_text(content, encoding="utf-8")
        return path

    def export_turn(self, turn: Turn, session: Session) -> Path:
        """Export a single turn as a standalone .md file."""
        self.output_dir.mkdir(parents=True, exist_ok=True)

        ts = turn.timestamp.strftime("%Y%m%d-%H%M%S")
        slug = self._slugify(turn.question[:40])
        filename = f"turn-{turn.question_number:02d}-{ts}-{slug}.md"
        path = self.output_dir / filename

        content = self._render_single_turn(turn, session)
        path.write_text(content, encoding="utf-8")
        return path

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------

    def _render(self, session: Session) -> str:
        parts: list[str] = []

        # Frontmatter
        parts.append("---")
        parts.append(f"title: \"{self._escape_yaml(session.title)}\"")
        parts.append(f"date: {session.created_at.isoformat()}")
        parts.append(f"session_id: {session.session_id}")
        parts.append(f"model: {session.model}")
        parts.append(f"questions: {session.question_count}")
        parts.append("---")
        parts.append("")

        # Header
        parts.append(f"# 🧮 {session.title}")
        parts.append("")
        parts.append(f"**会话 ID**: `{session.session_id}`  ")
        parts.append(f"**日期**: {session.created_at.strftime('%Y-%m-%d %H:%M')}  ")
        parts.append(f"**模型**: {session.model}  ")
        parts.append(f"**问题数**: {session.question_count}")
        parts.append("")
        parts.append("---")
        parts.append("")

        # Each turn
        for turn in session.turns:
            parts.append(self._render_turn(turn))
            parts.append("")

        # Footer
        parts.append("---")
        parts.append("")
        parts.append(
            f"*由 [MathAssistant](https://github.com) 自动生成 — "
            f"{session.created_at.strftime('%Y-%m-%d %H:%M')}*"
        )
        parts.append("")

        return "\n".join(parts)

    def _render_turn(self, turn: Turn) -> str:
        lines: list[str] = []

        # Question header
        lines.append(
            f"## Q{turn.question_number}: {turn.question}"
        )
        lines.append("")
        lines.append(f"**时间**: {turn.timestamp.strftime('%H:%M:%S')}")
        lines.append("")

        # Answer body
        if turn.answer:
            lines.append("### 📝 回答")
            lines.append("")
            lines.append(turn.answer.strip())
            lines.append("")

        # Tool calls
        if turn.tool_calls:
            for i, tc in enumerate(turn.tool_calls, 1):
                lines.append("### 🔧 工具调用")
                lines.append("")
                lines.append(f"<details>")
                lines.append(f"<summary>{tc.name} ({'❌ 出错' if tc.error else '✓'})</summary>")
                lines.append("")

                # Input code
                code = tc.input_args.get("code", "")
                if code:
                    lines.append("```python")
                    lines.append(code.strip())
                    lines.append("```")
                elif tc.input_args:
                    lines.append("```json")
                    lines.append(
                        json.dumps(tc.input_args, ensure_ascii=False, indent=2)
                    )
                    lines.append("```")

                # Output
                if tc.output:
                    lines.append("")
                    lines.append("**输出:**")
                    lines.append("")
                    lines.append("```")
                    lines.append(self._truncate(tc.output, 2000))
                    lines.append("```")

                lines.append("")
                lines.append("</details>")
                lines.append("")

        # Images
        if turn.images:
            lines.append("### 📊 图表")
            lines.append("")
            for img in turn.images:
                alt = self._image_alt(img)
                # Use relative path — the md file is in sessions/, images are in images/
                lines.append(f"![{alt}](../{img})")
                lines.append("")
                lines.append(f"*{alt}*")
                lines.append("")

        lines.append("---")
        return "\n".join(lines)

    def _render_single_turn(self, turn: Turn, session: Session) -> str:
        """Render one turn as a standalone .md (no frontmatter needed)."""
        parts: list[str] = []
        parts.append(
            f"# Q: {turn.question}"
        )
        parts.append("")
        parts.append(f"**会话**: {session.session_id} | **时间**: {turn.timestamp.isoformat()}")
        parts.append("")
        parts.append(self._render_turn_body(turn))
        return "\n".join(parts)

    def _render_turn_body(self, turn: Turn) -> str:
        """Just the body of a turn (used by single-turn export)."""
        lines: list[str] = []
        if turn.answer:
            lines.append(turn.answer.strip())
            lines.append("")
        for tc in turn.tool_calls:
            code = tc.input_args.get("code", "")
            if code:
                lines.append("```python")
                lines.append(code.strip())
                lines.append("```")
            if tc.output:
                lines.append("```")
                lines.append(self._truncate(tc.output, 2000))
                lines.append("```")
            lines.append("")
        for img in turn.images:
            alt = self._image_alt(img)
            lines.append(f"![{alt}](../{img})")
            lines.append("")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _filename(session: Session) -> str:
        ts = session.created_at.strftime("%Y%m%d-%H%M%S")
        slug = MarkdownExporter._slugify(session.title[:60])
        return f"session-{ts}-{slug}.md"

    @staticmethod
    def _slugify(text: str) -> str:
        """Convert arbitrary text to a safe filename slug."""
        import re
        slug = text.lower().strip()
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[-\s]+', '-', slug)
        return slug.strip('-') or "math"

    @staticmethod
    def _escape_yaml(text: str) -> str:
        return text.replace('"', '\\"').replace('\n', ' ')

    @staticmethod
    def _truncate(text: str, max_len: int = 2000) -> str:
        if len(text) <= max_len:
            return text
        return text[:max_len] + f"\n\n... (输出被截断，共 {len(text)} 字符)"

    @staticmethod
    def _image_alt(path: str) -> str:
        """Derive a human-readable caption from an image filename."""
        name = Path(path).stem
        # snake_case → Title Case
        return name.replace("_", " ").title()


# ---------------------------------------------------------------------------
# HTML Exporter
# ---------------------------------------------------------------------------

class HTMLExporter:
    """Export a Session to a self-contained HTML file.

    Features:
    - KaTeX CDN for LaTeX rendering (zero server-side dependency)
    - Images embedded as base64 data URIs (truly self-contained)
    - Dark/light theme via ``prefers-color-scheme``
    - Responsive layout, works on mobile/tablet/desktop
    - Collapsible tool-call sections
    - Print-friendly CSS
    """

    # If True, embed KaTeX locally instead of using CDN (much larger file)
    EMBED_KATEX = False

    KATEX_CDN_CSS = (
        "https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css"
    )
    KATEX_CDN_JS = (
        "https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"
    )
    KATEX_CDN_AUTO = (
        "https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/"
        "auto-render.min.js"
    )

    def __init__(
        self,
        output_dir: str = "./sessions",
        image_dir: str = "./images",
        embed_images: bool = True,
    ) -> None:
        self.output_dir = Path(output_dir)
        self.image_dir = Path(image_dir)
        self.embed_images = embed_images

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def export(self, session: Session) -> Path:
        """Export a full session as a self-contained .html file."""
        self.output_dir.mkdir(parents=True, exist_ok=True)

        filename = self._filename(session)
        path = self.output_dir / filename

        # We write a compact representation; the static method handles the
        # heavy lifting so we can test it independently.
        html = self._render(session)
        path.write_text(html, encoding="utf-8")
        return path

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------

    def _render(self, session: Session) -> str:
        """Produce the full HTML document string."""
        body = self._render_body(session)
        return self._html_shell(session, body)

    def _render_body(self, session: Session) -> str:
        parts: list[str] = []

        # Header
        parts.append('<header class="session-header">')
        parts.append(f'<h1>🧮 {self._escape(session.title)}</h1>')
        parts.append('<div class="meta">')
        parts.append(
            f'<span>会话 ID <code>{session.session_id}</code></span>'
        )
        parts.append(
            f'<span>日期 {session.created_at.strftime("%Y-%m-%d %H:%M")}</span>'
        )
        parts.append(f'<span>模型 {session.model}</span>')
        parts.append(f'<span>{session.question_count} 个问题</span>')
        parts.append('</div>')
        parts.append('</header>')

        # Turns
        for turn in session.turns:
            parts.append(self._render_turn(turn))

        # Footer
        parts.append('<footer class="session-footer">')
        parts.append(
            f'<p>由 MathAssistant 自动生成 — '
            f'{session.created_at.strftime("%Y-%m-%d %H:%M")}</p>'
        )
        parts.append('</footer>')

        return "\n".join(parts)

    def _render_turn(self, turn: Turn) -> str:
        lines: list[str] = []

        lines.append(f'<section class="turn" id="q{turn.question_number}">')
        lines.append(
            f'<h2>Q{turn.question_number}: {self._escape(turn.question)}</h2>'
        )
        lines.append(
            f'<time>{turn.timestamp.strftime("%H:%M:%S")}</time>'
        )

        # Answer
        if turn.answer:
            lines.append('<div class="answer">')
            lines.append(self._process_math_markup(turn.answer))
            lines.append('</div>')

        # Tool calls
        if turn.tool_calls:
            for tc in turn.tool_calls:
                lines.append(self._render_tool_call(tc))

        # Images
        if turn.images:
            lines.append('<div class="images-gallery">')
            lines.append('<h3>📊 图表</h3>')
            for img in turn.images:
                lines.append(self._render_image(img))
            lines.append('</div>')

        lines.append('</section>')
        return "\n".join(lines)

    def _render_tool_call(self, tc: ToolCallRecord) -> str:
        lines: list[str] = []
        status = '❌ 出错' if tc.error else '✓'
        safe_id = self._safe_id(tc.name)

        lines.append(f'<details class="tool-call">')
        lines.append(
            f'<summary>🔧 {tc.name} <span class="tool-status">{status}</span>'
            f'</summary>'
        )

        # Input
        code = tc.input_args.get("code", "")
        if code:
            lines.append('<pre><code class="language-python">')
            lines.append(self._escape(code.strip()))
            lines.append('</code></pre>')
        elif tc.input_args:
            lines.append('<pre><code class="language-json">')
            lines.append(
                self._escape(
                    json.dumps(tc.input_args, ensure_ascii=False, indent=2)
                )
            )
            lines.append('</code></pre>')

        # Output
        if tc.output:
            lines.append('<div class="tool-output">')
            lines.append('<strong>输出:</strong>')
            lines.append('<pre><code>')
            lines.append(
                self._escape(MarkdownExporter._truncate(tc.output, 2000))
            )
            lines.append('</code></pre>')
            lines.append('</div>')

        lines.append('</details>')
        return "\n".join(lines)

    def _render_image(self, img_path: str) -> str:
        """Render an ``<img>`` tag, optionally with base64 data URI."""
        alt = MarkdownExporter._image_alt(img_path)

        if self.embed_images:
            data_uri = self._image_to_data_uri(img_path)
            if data_uri:
                return (
                    f'<figure>\n'
                    f'  <img src="{data_uri}" alt="{alt}" '
                    f'loading="lazy">\n'
                    f'  <figcaption>{alt}</figcaption>\n'
                    f'</figure>'
                )

        # Fallback: relative path
        return (
            f'<figure>\n'
            f'  <img src="../{img_path}" alt="{alt}" '
            f'loading="lazy">\n'
            f'  <figcaption>{alt}</figcaption>\n'
            f'</figure>'
        )

    # ------------------------------------------------------------------
    # Image base64 encoding
    # ------------------------------------------------------------------

    def _image_to_data_uri(self, img_path: str) -> Optional[str]:
        """Convert a local image to a base64 data URI."""
        # Try relative to cwd first, then absolute
        candidate = self.image_dir.parent / img_path
        if not candidate.exists():
            candidate = Path(img_path)

        if not candidate.exists():
            return None

        try:
            mime_type = (
                mimetypes.guess_type(str(candidate))[0] or "image/png"
            )
            data = candidate.read_bytes()
            encoded = base64.b64encode(data).decode("ascii")
            return f"data:{mime_type};base64,{encoded}"
        except (OSError, ValueError):
            return None

    # ------------------------------------------------------------------
    # LaTeX / markup processing
    # ------------------------------------------------------------------

    def _process_math_markup(self, text: str) -> str:
        """Convert markdown-ish text to HTML, preserving LaTeX delimiters.

        KaTeX's auto-render will process ``$...$`` and ``$$...$$`` client-side.
        We just need to escape HTML and convert basic markdown.
        """
        # Escape HTML first
        out = self._escape(text)

        # Convert markdown headings (### Title → <h4>Title</h4>)
        import re
        out = re.sub(
            r'^### (.+)$', r'<h4>\1</h4>',
            out, flags=re.MULTILINE,
        )
        out = re.sub(
            r'^## (.+)$', r'<h3>\1</h3>',
            out, flags=re.MULTILINE,
        )

        # Bold (**text**)
        out = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', out)

        # Inline code (`code`)
        out = re.sub(r'`([^`]+)`', r'<code>\1</code>', out)

        # Convert double-newlines to paragraphs
        paragraphs = out.split('\n\n')
        processed = []
        for p in paragraphs:
            p = p.strip()
            if not p:
                continue
            # Don't wrap headings
            if p.startswith('<h'):
                processed.append(p)
            # Don't wrap details/section
            elif p.startswith('<'):
                processed.append(p)
            else:
                # Replace single newlines with <br> within paragraphs
                p = p.replace('\n', '<br>\n')
                processed.append(f'<p>{p}</p>')
        out = '\n'.join(processed)

        return out

    # ------------------------------------------------------------------
    # HTML Shell
    # ------------------------------------------------------------------

    def _html_shell(self, session: Session, body: str) -> str:
        """Wrap body content in a complete HTML document."""
        return (
            '<!DOCTYPE html>\n'
            '<html lang="zh-CN">\n'
            '<head>\n'
            '<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
            f'<title>{self._escape(session.title)} — MathAssistant</title>\n'
            f'{self._katex_head()}\n'
            f'{self._css()}\n'
            '</head>\n'
            '<body>\n'
            '<main class="container">\n'
            f'{body}\n'
            '</main>\n'
            f'{self._katex_script()}\n'
            '</body>\n'
            '</html>'
        )

    def _katex_head(self) -> str:
        if self.EMBED_KATEX:
            # Placeholder: embed KaTeX files inline
            return (
                '<!-- KaTeX would be embedded here for offline use -->\n'
                f'<link rel="stylesheet" href="{self.KATEX_CDN_CSS}">'
            )
        return (
            f'<link rel="stylesheet" href="{self.KATEX_CDN_CSS}">'
        )

    def _katex_script(self) -> str:
        return textwrap.dedent(f"""\
        <script src="{self.KATEX_CDN_JS}"></script>
        <script src="{self.KATEX_CDN_AUTO}"></script>
        <script>
          document.addEventListener("DOMContentLoaded", function() {{
            renderMathInElement(document.body, {{
              delimiters: [
                {{left: '$$', right: '$$', display: true}},
                {{left: '$',  right: '$',  display: false}},
                {{left: '\\\\[', right: '\\\\]', display: true}},
                {{left: '\\\\(', right: '\\\\)', display: false}},
              ],
              throwOnError: false
            }});
          }});
        </script>
        """)

    def _css(self) -> str:
        """Return the complete CSS for the HTML export."""
        return textwrap.dedent("""\
        <style>
        /* ============================================================
           MathAssistant — Light/Dark Theme
           ============================================================ */
        :root {
          --bg: #ffffff;
          --bg-secondary: #f8f9fa;
          --text: #1a1a2e;
          --text-secondary: #555;
          --border: #e0e0e0;
          --accent: #2563eb;
          --accent-hover: #1d4ed8;
          --code-bg: #f1f3f5;
          --tool-bg: #f8f9fa;
          --shadow: 0 1px 3px rgba(0,0,0,0.08);
          --radius: 8px;
        }

        @media (prefers-color-scheme: dark) {
          :root {
            --bg: #1a1a2e;
            --bg-secondary: #16213e;
            --text: #e0e0e0;
            --text-secondary: #a0a0b0;
            --border: #2a2a4a;
            --accent: #60a5fa;
            --accent-hover: #93bbfd;
            --code-bg: #0f3460;
            --tool-bg: #16213e;
            --shadow: 0 1px 3px rgba(0,0,0,0.3);
          }
        }

        /* ----------------------------------------------------------
           Base
           ---------------------------------------------------------- */
        *, *::before, *::after { box-sizing: border-box; }
        html { font-size: 16px; -webkit-text-size-adjust: 100%; }
        body {
          font-family: system-ui, -apple-system, "Segoe UI", Roboto,
                       "Noto Sans SC", "PingFang SC", "Microsoft YaHei",
                       sans-serif;
          background: var(--bg);
          color: var(--text);
          line-height: 1.75;
          margin: 0;
          padding: 0;
        }

        .container {
          max-width: 820px;
          margin: 0 auto;
          padding: 2rem 1.5rem;
        }

        /* ----------------------------------------------------------
           Typography
           ---------------------------------------------------------- */
        h1 { font-size: 1.8rem; margin: 0 0 0.5rem; color: var(--text); }
        h2 {
          font-size: 1.35rem; margin: 2.5rem 0 0.75rem;
          padding-bottom: 0.4rem; border-bottom: 1px solid var(--border);
          color: var(--text);
        }
        h3 { font-size: 1.15rem; margin: 1.5rem 0 0.5rem; }
        h4 { font-size: 1.05rem; margin: 1.2rem 0 0.4rem; }
        p { margin: 0.75rem 0; }
        a { color: var(--accent); text-decoration: none; }
        a:hover { text-decoration: underline; color: var(--accent-hover); }
        code {
          background: var(--code-bg);
          padding: 0.15em 0.35em;
          border-radius: 3px;
          font-size: 0.9em;
          font-family: "JetBrains Mono", "Fira Code", "Cascadia Code",
                       "Consolas", "Monaco", monospace;
        }
        pre code {
          display: block;
          padding: 1rem 1.2rem;
          overflow-x: auto;
          border-radius: var(--radius);
          line-height: 1.55;
          background: var(--code-bg);
        }

        /* ----------------------------------------------------------
           Session Header
           ---------------------------------------------------------- */
        .session-header {
          text-align: center;
          padding: 2rem 0 1.5rem;
          border-bottom: 2px solid var(--border);
          margin-bottom: 2rem;
        }
        .session-header .meta {
          display: flex;
          flex-wrap: wrap;
          justify-content: center;
          gap: 0.5rem 1.5rem;
          color: var(--text-secondary);
          font-size: 0.9rem;
          margin-top: 0.5rem;
        }

        /* ----------------------------------------------------------
           Turns
           ---------------------------------------------------------- */
        .turn {
          margin-bottom: 2.5rem;
          padding: 1.5rem;
          background: var(--bg-secondary);
          border-radius: var(--radius);
          box-shadow: var(--shadow);
          border: 1px solid var(--border);
        }
        .turn time {
          display: block;
          font-size: 0.8rem;
          color: var(--text-secondary);
          margin-bottom: 1rem;
        }
        .answer {
          margin: 1rem 0;
        }
        .answer p {
          margin: 0.6rem 0;
        }

        /* ----------------------------------------------------------
           Tool Calls
           ---------------------------------------------------------- */
        .tool-call {
          margin: 1rem 0;
          padding: 0.75rem 1rem;
          background: var(--tool-bg);
          border: 1px solid var(--border);
          border-radius: var(--radius);
        }
        .tool-call summary {
          cursor: pointer;
          font-weight: 600;
          color: var(--accent);
          padding: 0.25rem 0;
        }
        .tool-call summary:hover {
          color: var(--accent-hover);
        }
        .tool-call .tool-status {
          font-size: 0.85rem;
          color: var(--text-secondary);
        }
        .tool-call[open] {
          padding-bottom: 1rem;
        }
        .tool-output {
          margin-top: 0.5rem;
        }
        .tool-output strong {
          display: block;
          margin-bottom: 0.25rem;
          font-size: 0.9rem;
          color: var(--text-secondary);
        }

        /* ----------------------------------------------------------
           Images
           ---------------------------------------------------------- */
        .images-gallery {
          margin: 1.5rem 0;
        }
        .images-gallery h3 {
          margin-bottom: 0.75rem;
        }
        figure {
          margin: 1rem 0;
          text-align: center;
        }
        figure img {
          max-width: 100%;
          height: auto;
          border-radius: var(--radius);
          border: 1px solid var(--border);
          box-shadow: var(--shadow);
        }
        figcaption {
          margin-top: 0.4rem;
          font-size: 0.9rem;
          color: var(--text-secondary);
          font-style: italic;
        }

        /* ----------------------------------------------------------
           Footer
           ---------------------------------------------------------- */
        .session-footer {
          margin-top: 3rem;
          padding-top: 1.5rem;
          border-top: 1px solid var(--border);
          text-align: center;
          font-size: 0.85rem;
          color: var(--text-secondary);
        }

        /* ----------------------------------------------------------
           KaTeX overrides
           ---------------------------------------------------------- */
        .katex-display {
          margin: 1rem 0;
          overflow-x: auto;
          overflow-y: hidden;
        }
        .katex {
          font-size: 1.1em;
        }

        /* ----------------------------------------------------------
           Print
           ---------------------------------------------------------- */
        @media print {
          :root {
            --bg: #ffffff;
            --text: #000000;
            --text-secondary: #555;
            --border: #ccc;
            --code-bg: #f5f5f5;
            --tool-bg: #fafafa;
          }
          .turn { break-inside: avoid; box-shadow: none; }
          .tool-call { break-inside: avoid; }
          body { font-size: 12pt; }
          .container { max-width: 100%; padding: 0; }
        }

        /* ----------------------------------------------------------
           Responsive
           ---------------------------------------------------------- */
        @media (max-width: 640px) {
          .container { padding: 1rem; }
          .turn { padding: 1rem; }
          h1 { font-size: 1.4rem; }
          h2 { font-size: 1.15rem; }
          .session-header .meta { flex-direction: column; gap: 0.25rem; }
        }
        </style>
        """)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _escape(text: str) -> str:
        """Minimal HTML escaping."""
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    @staticmethod
    def _filename(session: Session) -> str:
        ts = session.created_at.strftime("%Y%m%d-%H%M%S")
        slug = MarkdownExporter._slugify(session.title[:60])
        return f"session-{ts}-{slug}.html"

    @staticmethod
    def _safe_id(text: str) -> str:
        """Create a safe HTML id from arbitrary text."""
        import re
        return re.sub(r'[^a-zA-Z0-9_-]', '-', text)[:40]
