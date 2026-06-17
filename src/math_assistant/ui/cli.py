"""CLI terminal UI for MathAssistant.

Uses the Rich library for formatted output with colors and panels.
"""

import json
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

from .base import AbstractUI


class CLIUI(AbstractUI):
    """Rich-powered terminal UI for MathAssistant."""

    def __init__(self):
        self.console = Console()

    def display_welcome(self) -> None:
        from ..prompts import WELCOME_MESSAGE
        self.console.print(WELCOME_MESSAGE)

    def display_assistant_message(self, content: str) -> None:
        self.console.print()
        self.console.print(Markdown(content))
        self.console.print()

    def display_tool_call(self, tool_name: str, tool_input: dict[str, Any]) -> None:
        # Format tool input nicely
        if tool_name == "execute_python":
            code = tool_input.get("code", "")
            preview = code[:200] + "..." if len(code) > 200 else code
            self.console.print(
                Panel(
                    preview,
                    title=f"[bold cyan]⚙ Running Python[/bold cyan]",
                    border_style="cyan",
                )
            )
        elif tool_name == "web_search":
            query = tool_input.get("query", "")
            self.console.print(
                Panel(
                    f"Searching for: [italic]{query}[/italic]",
                    title=f"[bold green]🔍 {tool_name}[/bold green]",
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
        # Show truncated result
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

    def display_error(self, message: str) -> None:
        self.console.print(f"\n[bold red]Error:[/bold red] {message}\n")

    def display_thinking(self) -> None:
        self.console.print("[dim]Thinking...[/dim]", end="\r")

    def get_user_input(self) -> str:
        return self.console.input("\n[bold green]You:[/bold green] ").strip()

    def display_goodbye(self) -> None:
        self.console.print("\n[bold]Goodbye! Keep exploring the beauty of mathematics. 👋[/bold]\n")
