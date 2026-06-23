"""Abstract UI interface for MathAssistant.

UI implementations (CLI, Gradio, Streamlit) must implement this interface.
This makes the agent logic completely decoupled from the UI layer.
"""

from abc import ABC, abstractmethod
from typing import Any


class AbstractUI(ABC):
    """Abstract base for MathAssistant user interfaces."""

    @abstractmethod
    def display_welcome(self) -> None:
        """Show the welcome / startup message."""
        ...

    @abstractmethod
    def display_assistant_message(self, content: str) -> None:
        """Render an assistant text message to the user."""
        ...

    @abstractmethod
    def display_tool_call(self, tool_name: str, tool_input: dict[str, Any]) -> None:
        """Indicate that the agent is calling a tool."""
        ...

    @abstractmethod
    def display_tool_result(self, tool_name: str, result: str) -> None:
        """Display the result of a tool call (truncated if needed)."""
        ...

    @abstractmethod
    def display_step(self, node_name: str, step_number: int) -> None:
        """Display the current execution step."""
        ...

    @abstractmethod
    def display_tool_calls(self, tool_calls: list[dict[str, Any]]) -> None:
        """Display pending tool calls from an AI message."""
        ...

    @abstractmethod
    def display_error(self, message: str) -> None:
        """Display an error message."""
        ...

    @abstractmethod
    def display_thinking(self) -> None:
        """Show a 'thinking' indicator."""
        ...

    @abstractmethod
    def get_user_input(self) -> str:
        """Get input from the user. Blocking call."""
        ...

    @abstractmethod
    def display_goodbye(self) -> None:
        """Show the goodbye message."""
        ...
