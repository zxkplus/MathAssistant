"""CLI entry point for MathAssistant.

Parses command-line arguments, loads configuration, creates the agent,
and runs an interactive REPL loop for multi-turn math conversations.

Optional backend integration: use --backend-url to connect to a
MathAssistant backend server for user management and learning analytics.
"""

import argparse
import json
import sys
import uuid
from pathlib import Path
from typing import Any, Optional

from langchain.messages import HumanMessage

from .config import Config
from .agent import create_math_agent
from .ui.cli import CLIUI
from .ui.base import AbstractUI
from .session.recorder import SessionRecorder
from .session.exporter import MarkdownExporter, HTMLExporter


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="MathAssistant — AI-powered mathematics teacher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m math_assistant.main
  python -m math_assistant.main --config /path/to/config.yaml
  python -m math_assistant.main --api-key sk-xxx --model deepseek-chat
  python -m math_assistant.main --backend-url http://127.0.0.1:8000 --backend-user alice
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
    parser.add_argument(
        "--backend-url",
        type=str,
        default=None,
        help="URL of MathAssistant backend server for user management and analytics",
    )
    parser.add_argument(
        "--backend-user",
        type=str,
        default=None,
        help="Username for backend authentication",
    )
    parser.add_argument(
        "--backend-password",
        type=str,
        default=None,
        help="Password for backend authentication (use stdin if not provided)",
    )
    return parser.parse_args()


def _save_session(
    session_recorder: SessionRecorder,
    config: Config,
    ui: AbstractUI,
) -> None:
    """Save the current session as .md (and optionally .html)."""
    session = session_recorder.session
    if session.question_count == 0:
        ui.display_error("Nothing to save — the session is empty.")
        return

    save_dir = config.output.save_dir
    image_dir = config.output.image_dir

    # Always export Markdown
    md_exporter = MarkdownExporter(output_dir=save_dir)
    md_path = md_exporter.export(session)
    ui.display_assistant_message(f"📄 Markdown saved: {md_path}")

    # Optionally export HTML
    if config.output.html_export:
        html_exporter = HTMLExporter(
            output_dir=save_dir,
            image_dir=image_dir,
            embed_images=config.output.embed_images,
        )
        html_path = html_exporter.export(session)
        ui.display_assistant_message(f"🌐 HTML saved: {html_path}")


def _handle_command(
    user_input: str,
    session_recorder: SessionRecorder,
    config: Config,
    ui: AbstractUI,
    backend_client: Optional[Any] = None,
    last_question_id: Optional[int] = None,
) -> tuple[bool, Optional[int]]:
    """Handle REPL meta-commands.

    Returns (was_handled, new_last_question_id).
    was_handled=True means skip agent processing.
    """
    cmd = user_input.strip().lower()

    # --- quit commands ---
    if cmd in (":quit", ":exit", ":q", "quit", "exit", "q"):
        ui.display_goodbye()
        sys.exit(0)

    # --- session reset ---
    if cmd in (":new", ":reset", ":clear", "new", "reset", "clear"):
        _save_session(session_recorder, config, ui)
        session_recorder.new_session()
        ui.display_assistant_message(
            "✨ Starting a new conversation! What would you like to explore?"
        )
        return True, None

    # --- save commands ---
    if cmd in (":save", ":save md", ":save markdown"):
        _save_session(session_recorder, config, ui)
        return True, last_question_id

    if cmd == ":save html":
        session = session_recorder.session
        if session.question_count == 0:
            ui.display_error("Nothing to export.")
            return True, last_question_id
        html_exporter = HTMLExporter(
            output_dir=config.output.save_dir,
            image_dir=config.output.image_dir,
            embed_images=config.output.embed_images,
        )
        path = html_exporter.export(session)
        ui.display_assistant_message(f"🌐 HTML exported: {path}")
        return True, last_question_id

    if cmd in (":export", ":export html"):
        session = session_recorder.session
        if session.question_count == 0:
            ui.display_error("Nothing to export.")
            return True, last_question_id
        md_exporter = MarkdownExporter(output_dir=config.output.save_dir)
        md_path = md_exporter.export(session)
        ui.display_assistant_message(f"📄 Markdown: {md_path}")
        html_exporter = HTMLExporter(
            output_dir=config.output.save_dir,
            image_dir=config.output.image_dir,
            embed_images=config.output.embed_images,
        )
        html_path = html_exporter.export(session)
        ui.display_assistant_message(f"🌐 HTML: {html_path}")
        return True, last_question_id

    if cmd in (":export md", ":export markdown"):
        session = session_recorder.session
        if session.question_count == 0:
            ui.display_error("Nothing to export.")
            return True, last_question_id
        md_exporter = MarkdownExporter(output_dir=config.output.save_dir)
        path = md_exporter.export(session)
        ui.display_assistant_message(f"📄 Markdown exported: {path}")
        return True, last_question_id

    # --- Backend commands (only available when backend is connected) ---
    if backend_client is not None:
        if cmd in (":correct", ":c"):
            if last_question_id is None:
                ui.display_error("No question to mark as correct.")
            else:
                try:
                    backend_client.record_answer(last_question_id, is_correct=True)
                    ui.display_assistant_message("✅ Marked as correct. Mastery scores updated.")
                except Exception as e:
                    ui.display_error(f"Failed to record answer: {e}")
            return True, last_question_id

        if cmd in (":wrong", ":w"):
            if last_question_id is None:
                ui.display_error("No question to mark as wrong.")
            else:
                try:
                    backend_client.record_answer(last_question_id, is_correct=False)
                    ui.display_assistant_message("❌ Marked as incorrect. Added to mistake notebook.")
                except Exception as e:
                    ui.display_error(f"Failed to record answer: {e}")
            return True, last_question_id

        if cmd == ":stats":
            try:
                summary = backend_client.get_summary()
                mastery = backend_client.get_mastery()
                ui.display_assistant_message(f"""**📊 Learning Statistics**
- Questions: {summary['total_questions']} | Accuracy: {summary['overall_accuracy']}%
- Sessions: {summary['total_sessions']} | Study Time: {summary['total_study_minutes']} min
- Topics Explored: {summary['topics_explored']} | Streak: {summary['streak_days']} days

**Overall Mastery Score: {mastery['overall_score']}/100**
**Strongest Areas:** {', '.join(a['name'] for a in summary['strongest_areas'][:3]) or 'Not enough data'}
**Weakest Areas:** {', '.join(a['name'] for a in summary['weakest_areas'][:3]) or 'Not enough data'}
""")
            except Exception as e:
                ui.display_error(f"Failed to fetch stats: {e}")
            return True, last_question_id

        if cmd == ":mistakes":
            try:
                nb = backend_client.get_mistake_notebook(limit=5)
                if not nb["items"]:
                    ui.display_assistant_message("No mistakes recorded yet! 🎉")
                else:
                    lines = ["**📝 Recent Mistakes:**"]
                    for i, item in enumerate(nb["items"], 1):
                        preview = item["question_content"][:80]
                        kp = item.get("knowledge_point_name") or "N/A"
                        mt = item.get("mistake_type") or "unknown"
                        lines.append(f"{i}. [{kp}] {preview}... (`{mt}`)")
                    ui.display_assistant_message("\n".join(lines))
            except Exception as e:
                ui.display_error(f"Failed to fetch mistakes: {e}")
            return True, last_question_id

        if cmd == ":recommend":
            try:
                recs = backend_client.get_recommendations(limit=5)
                if not recs["items"]:
                    ui.display_assistant_message("No recommendations yet — keep practicing!")
                else:
                    lines = ["**🎯 Learning Recommendations:**"]
                    for i, r in enumerate(recs["items"], 1):
                        actions = "; ".join(
                            a["description"] for a in r["suggested_actions"]
                        )
                        lines.append(
                            f"{i}. **{r['name']}** (score: {r['current_score']:.0f}/100)\n"
                            f"   → {actions}"
                        )
                    ui.display_assistant_message("\n".join(lines))
            except Exception as e:
                ui.display_error(f"Failed to fetch recommendations: {e}")
            return True, last_question_id

    # --- help ---
    if cmd in (":help", ":h", "help"):
        backend_cmds = ""
        if backend_client is not None:
            backend_cmds = """
**Backend Commands (with --backend-url):**
- `:correct` / `:c` — mark last answer as correct
- `:wrong` / `:w` — mark last answer as incorrect
- `:stats` — show learning statistics and mastery summary
- `:mistakes` — show recent mistakes (错题本)
- `:recommend` — show learning recommendations
"""
        ui.display_assistant_message(f"""
**Commands:**
- `:save` / `:export` — save session as Markdown + HTML
- `:save md` / `:export md` — save as Markdown only
- `:save html` / `:export html` — export as self-contained HTML
- `:new` / `reset` — start a new session (auto-saves the current one)
- `:quit` / `exit` — exit (auto-saves)
- `:help` — show this message
{backend_cmds}
""")
        return True, last_question_id

    return False, last_question_id


def run_repl(
    agent,
    ui: AbstractUI,
    config: Config,
    backend_client: Optional[Any] = None,
) -> None:
    """Run the interactive REPL loop.

    Each conversation turn is associated with a thread_id for
    multi-turn memory via the MemorySaver checkpointer.

    Args:
        agent: The compiled LangGraph agent.
        ui: The UI implementation.
        config: Application configuration.
        backend_client: Optional MathAssistantBackendClient for
                        user management and analytics.
    """
    session_id = str(uuid.uuid4())[:8]
    graph_config: dict[str, Any] = {"configurable": {"thread_id": session_id}}

    # Session recorder for export
    session_recorder = SessionRecorder(
        model=config.main.model,
        image_dir=config.output.image_dir,
    )

    # Track the last submitted question ID for answer recording
    last_question_id: Optional[int] = None

    ui.display_welcome()

    if backend_client is not None and backend_client.is_authenticated:
        ui.display_assistant_message(
            "🔗 Connected to backend — use :correct/:wrong to record answers, "
            ":stats for analytics."
        )

    while True:
        try:
            user_input = ui.get_user_input()
        except (KeyboardInterrupt, EOFError):
            ui.display_goodbye()
            break

        if not user_input:
            continue

        # Check for meta-commands (both `:cmd` style and legacy bare words)
        handled, last_question_id = _handle_command(
            user_input, session_recorder, config, ui,
            backend_client, last_question_id,
        )
        if handled:
            continue

        # --- Start a new turn ---
        session_recorder.start_turn(user_input)

        # Submit question to backend if connected
        if backend_client is not None and backend_client.is_authenticated:
            try:
                result = backend_client.submit_question(user_input, source="cli")
                last_question_id = result["id"]
            except Exception:
                last_question_id = None

        # Process the message
        try:
            ui.display_thinking()
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
                            # --- Accumulate text for recorder ---
                            if msg.content:
                                if isinstance(msg.content, str) and msg.content.strip():
                                    session_recorder.add_assistant_text(msg.content)
                                    ui.display_assistant_message(msg.content)
                                elif isinstance(msg.content, list):
                                    texts = []
                                    for block in msg.content:
                                        if isinstance(block, dict) and block.get("type") == "text":
                                            texts.append(block.get("text", ""))
                                    if texts:
                                        joined = "\n".join(texts)
                                        session_recorder.add_assistant_text(joined)
                                        ui.display_assistant_message(joined)

                            # --- Record tool calls ---
                            if hasattr(msg, "tool_calls") and msg.tool_calls:
                                ui.display_tool_calls(msg.tool_calls)
                                for tc in msg.tool_calls:
                                    session_recorder.record_tool_call(
                                        name=tc.get("name", "unknown"),
                                        args=tc.get("args", {}),
                                    )

                        elif type_name == "ToolMessage":
                            result_str = str(msg.content)
                            session_recorder.record_tool_result(
                                name=msg.name or "unknown",
                                output=result_str,
                            )
                            ui.display_tool_result(
                                tool_name=msg.name or "unknown",
                                result=result_str,
                            )

        except Exception as e:
            ui.display_error(str(e))

        # --- Finalize the turn ---
        session_recorder.end_turn()

        # Auto-save if mode is "turn"
        if config.output.save_mode == "turn":
            turn = session_recorder.session.turns[-1]
            md_exporter = MarkdownExporter(output_dir=config.output.save_dir)
            path = md_exporter.export_turn(turn, session_recorder.session)
            ui.display_assistant_message(f"📄 Turn saved: {path}")

    # --- Exit: auto-save session ---
    if config.output.save_mode == "session":
        _save_session(session_recorder, config, ui)


def main():
    args = parse_args()

    # Load configuration
    config = Config.load(config_path=args.config)

    # Apply CLI overrides
    if args.api_key:
        config.main.api_key = args.api_key
    if args.model:
        config.main.model = args.model

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

    # Optional backend client
    backend_client = None
    if args.backend_url:
        try:
            from .server.cli_client import MathAssistantBackendClient

            backend_client = MathAssistantBackendClient(base_url=args.backend_url)

            if args.backend_user:
                password = args.backend_password
                if not password:
                    import getpass
                    password = getpass.getpass(f"Password for {args.backend_user}: ")
                if password:
                    try:
                        result = backend_client.login(args.backend_user, password)
                        ui.display_assistant_message(
                            f"🔐 Logged in as {result['user']['username']}"
                        )
                    except Exception as e:
                        ui.display_error(f"Backend login failed: {e}")
                        ui.display_assistant_message(
                            "Continuing without backend. Use :help for available commands."
                        )
                        backend_client = None
        except ImportError:
            ui.display_error(
                "Backend dependencies not installed. "
                "Install with: pip install math-assistant[server]"
            )
            backend_client = None
        except Exception as e:
            ui.display_error(f"Failed to connect to backend: {e}")
            backend_client = None

    # Run the REPL
    run_repl(agent, ui, config, backend_client)


if __name__ == "__main__":
    main()
