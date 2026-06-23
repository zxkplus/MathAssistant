"""CLI entry point for MathAssistant.

Parses command-line arguments, loads configuration, creates the agent,
and runs an interactive REPL loop for multi-turn math conversations.
"""

import argparse
import sys
import uuid
from typing import Any

from langchain.messages import HumanMessage

from .config import Config
from .agent import create_math_agent
from .ui.cli import CLIUI
from .ui.base import AbstractUI


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="MathAssistant — AI-powered mathematics teacher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m math_assistant.main
  python -m math_assistant.main --config /path/to/config.yaml
  python -m math_assistant.main --api-key sk-xxx --model deepseek-chat
        """,
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to YAML config file (default: config.yaml in project root)",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="API key (overrides environment variables)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Model name (overrides config.yaml)",
    )
    return parser.parse_args()


def run_repl(agent, ui: AbstractUI, config: Config) -> None:
    """Run the interactive REPL loop.

    Each conversation turn is associated with a thread_id for
    multi-turn memory via the MemorySaver checkpointer.
    """
    session_id = str(uuid.uuid4())[:8]
    graph_config: dict[str, Any] = {"configurable": {"thread_id": session_id}}

    ui.display_welcome()

    while True:
        try:
            user_input = ui.get_user_input()
        except (KeyboardInterrupt, EOFError):
            ui.display_goodbye()
            break

        if not user_input:
            continue

        lower = user_input.strip().lower()
        if lower in ("quit", "exit", "q"):
            ui.display_goodbye()
            break

        if lower in ("new", "reset", "clear"):
            # Start a new session
            session_id = str(uuid.uuid4())[:8]
            graph_config["configurable"]["thread_id"] = session_id
            ui.display_assistant_message("Starting a new conversation! What would you like to explore?")
            continue

        # Process the message
        try:
            ui.display_thinking()
            # Use stream_mode="updates" to see each step in real time
            step_count = 0
            for chunk in agent.stream(
                {"messages": [HumanMessage(content=user_input)]},
                config=graph_config,
                stream_mode="updates",
            ):
                # chunk is a dict: {node_name: state_update}
                for node_name, state_update in chunk.items():
                    # Skip internal middleware nodes (only show "model" and "tools")
                    if node_name not in ("model", "tools"):
                        continue

                    step_count += 1
                    messages = state_update.get("messages", [])

                    # Display step indicator
                    ui.display_step(node_name, step_count)

                    for msg in messages:
                        type_name = type(msg).__name__

                        if type_name == "AIMessage":
                            if msg.content:
                                if isinstance(msg.content, str) and msg.content.strip():
                                    # Skip tool-call-only messages (content is empty or just a list)
                                    ui.display_assistant_message(msg.content)
                                elif isinstance(msg.content, list):
                                    texts = []
                                    for block in msg.content:
                                        if isinstance(block, dict) and block.get("type") == "text":
                                            texts.append(block.get("text", ""))
                                    if texts:
                                        ui.display_assistant_message("\n".join(texts))
                                # Show tool calls if any
                                if hasattr(msg, "tool_calls") and msg.tool_calls:
                                    ui.display_tool_calls(msg.tool_calls)

                        elif type_name == "ToolMessage":
                            ui.display_tool_result(
                                tool_name=msg.name or "unknown",
                                result=str(msg.content),
                            )

        except Exception as e:
            ui.display_error(str(e))


def main():
    args = parse_args()

    # Load configuration
    config = Config.load(config_path=args.config)

    # Apply CLI overrides
    if args.api_key:
        config.api.api_key = args.api_key
    if args.model:
        config.model.name = args.model

    # Validate API key
    try:
        config.get_api_key()
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Create the agent
    agent = create_math_agent(config)

    # Create the UI
    ui = CLIUI()

    # Run the REPL
    run_repl(agent, ui, config)


if __name__ == "__main__":
    main()
