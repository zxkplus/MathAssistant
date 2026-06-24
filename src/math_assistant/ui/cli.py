"""CLI terminal UI for MathAssistant.

Uses the Rich library for formatted output with colors and panels.
Integrates MathRenderer for LaTeX-to-Unicode math display in terminal.
"""

import json
import os
import re
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

from .base import AbstractUI
from .renderer import MathRenderer


def _detect_image_terminal() -> bool:
    """Check whether the terminal supports inline image display."""
    if "KITTY_WINDOW_ID" in os.environ:
        return True
    if "ITERM_SESSION_ID" in os.environ or os.environ.get("TERM_PROGRAM") == "iTerm.app":
        return True
    if os.environ.get("TERM_PROGRAM") == "WezTerm":
        return True
    return False


def _display_image_iterm(image_path: str) -> bool:
    """Display an image inline using iTerm2's OSC 1337 protocol."""
    import base64
    p = Path(image_path)
    if not p.exists():
        return False
    try:
        data = base64.b64encode(p.read_bytes()).decode("ascii")
        print(f"\033]1337;File=inline=1;size={len(data)}:{data}\a", end="")
        return True
    except Exception:
        return False


def _display_image_kitty(image_path: str) -> bool:
    """Display an image inline using Kitty's terminal protocol."""
    import subprocess
    p = Path(image_path)
    if not p.exists():
        return False
    try:
        result = subprocess.run(
            ["kitty", "+kitten", "icat", "--align", "left",
             "--place", "800x500@0x0", "--scale-up", str(p)],
            capture_output=True,
            timeout=10,
        )
        return result.returncode == 0
    except Exception:
        return False


class CLIUI(AbstractUI):
    """Rich-powered terminal UI with math rendering."""

    def __init__(self):
        self.console = Console()
        self._math = MathRenderer()
        self._supports_images = _detect_image_terminal()
        # Track which image terminal protocol to use
        self._img_backend = ""
        if self._supports_images:
            if "KITTY_WINDOW_ID" in os.environ:
                self._img_backend = "kitty"
            else:
                self._img_backend = "iterm"

    # ------------------------------------------------------------------
    # Display methods
    # ------------------------------------------------------------------

    def display_welcome(self) -> None:
        from ..prompts import WELCOME_MESSAGE
        self.console.print(WELCOME_MESSAGE)
        if self._supports_images:
            self.console.print(
                "[dim]🖼  Terminal image display: enabled[/dim]"
            )
        else:
            self.console.print(
                "[dim]💡 Tip: use iTerm2/Kitty/WezTerm for inline chart display[/dim]"
            )

    def display_assistant_message(self, content: str) -> None:
        # Enhance math formulas with Rich styling for terminal visibility
        wrapped = self._math.process_response(content)
        self.console.print()
        try:
            self.console.print(Markdown(wrapped))
        except Exception:
            # Fallback: plain print if Rich Markdown fails on complex content
            self.console.print(wrapped)
        self.console.print()

    def display_tool_call(self, tool_name: str, tool_input: dict[str, Any]) -> None:
        if tool_name == "execute_python":
            code = tool_input.get("code", "")
            preview = code[:200] + "..." if len(code) > 200 else code
            self.console.print(
                Panel(
                    preview,
                    title="[bold cyan]⚙ Running Python[/bold cyan]",
                    border_style="cyan",
                )
            )
        elif tool_name == "web_search":
            query = tool_input.get("query", "")
            self.console.print(
                Panel(
                    f"Searching for: [italic]{query}[/italic]",
                    title="[bold green]🔍 web_search[/bold green]",
                    border_style="green",
                )
            )
        else:
            self.console.print(
                Panel(
                    json.dumps(tool_input, ensure_ascii=False, indent=2),
                    title=f"[bold yellow]🔧 {tool_name}[/bold yellow]",
                    border_style="yellow",
                )
            )

    def display_tool_result(self, tool_name: str, result: str) -> None:
        # Truncate long results
        if len(result) > 500:
            preview = result[:500] + f"\n... (truncated, {len(result)} chars total)"
        else:
            preview = result
        self.console.print(
            Panel(
                preview,
                title=f"[bold]✅ {tool_name} result[/bold]",
                border_style="dim",
            )
        )
        # Try to display any images referenced in the result
        self._display_images_in_result(result)

    def display_step(self, node_name: str, step_number: int) -> None:
        emoji = "🤖" if node_name == "model" else "🔧"
        label = "Model" if node_name == "model" else "Tools"
        self.console.print(
            f"\n[dim]Step {step_number}: {emoji} {label} ({node_name})[/dim]"
        )

    def display_tool_calls(self, tool_calls: list[dict[str, Any]]) -> None:
        for tc in tool_calls:
            tool_name = tc.get("name", "unknown")
            args = tc.get("args", {})
            if tool_name == "execute_python":
                code = args.get("code", "")
                preview = code[:150] + "..." if len(code) > 150 else code
                self.console.print(
                    Panel(
                        preview,
                        title="[bold cyan]⚙ Python[/bold cyan]",
                        border_style="cyan",
                    )
                )
            elif tool_name == "web_search":
                query = args.get("query", "")
                self.console.print(
                    Panel(
                        f"Searching: [italic]{query}[/italic]",
                        title="[bold green]🔍 Search[/bold green]",
                        border_style="green",
                    )
                )
            else:
                self.console.print(
                    Panel(
                        json.dumps(args, ensure_ascii=False, indent=2),
                        title=f"[bold yellow]🔧 {tool_name}[/bold yellow]",
                        border_style="yellow",
                    )
                )

    def display_error(self, message: str) -> None:
        self.console.print(f"\n[bold red]Error:[/bold red] {message}\n")

    def display_thinking(self) -> None:
        self.console.print("[dim]Thinking...[/dim]", end="\r")

    def get_user_input(self) -> str:
        return self.console.input("\n[bold green]🧮 You:[/bold green] ").strip()

    def display_goodbye(self) -> None:
        self.console.print(
            "\n[bold]Goodbye! Keep exploring the beauty of mathematics. 👋[/bold]\n"
        )

    # ------------------------------------------------------------------
    # Inline image display
    # ------------------------------------------------------------------

    def _display_images_in_result(self, text: str) -> None:
        """Scan tool result for image paths and try to display them inline."""
        if not self._supports_images:
            return

        image_pattern = re.compile(
            r'(?:images?/[\w\-./]+\.(?:png|jpg|jpeg))', re.IGNORECASE
        )
        for match in image_pattern.finditer(text):
            path = match.group(0)
            full_path = Path(path)
            if not full_path.exists():
                continue
            self.console.print(f"[dim]📊 Displaying: {path}[/dim]")
            try:
                if self._img_backend == "kitty":
                    if _display_image_kitty(str(full_path)):
                        continue
                if _display_image_iterm(str(full_path)):
                    continue
                self.console.print(f"[dim yellow]   Image saved: {path}[/dim yellow]")
            except Exception:
                self.console.print(f"[dim yellow]   Image saved: {path}[/dim yellow]")
