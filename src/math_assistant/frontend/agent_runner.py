"""Agent runner — wraps create_math_agent() + agent.stream() for the frontend.

Yields structured step events that the Streamlit chat page can render
incrementally as the agent works through model and tool nodes.
"""

from typing import Any, Generator, Optional

from langchain.messages import HumanMessage

from math_assistant.config import Config
from math_assistant.agent import create_math_agent


def run_agent_stream(
    config: Config,
    user_input: str,
    thread_id: str,
    image_dir: str | None = None,
) -> Generator[dict[str, Any], None, None]:
    """Run the MathAssistant agent and yield structured step events.

    Each yielded dict has:
      - node: "model" or "tools"
      - type: "AIMessage" or "ToolMessage"
      - content: str (text content for AIMessage, tool output for ToolMessage)
      - tool_calls: list[dict] | None (only on AIMessage)
      - tool_name: str | None (only on ToolMessage)

    Args:
        config: Application config with LLM settings.
        user_input: The user's question text.
        thread_id: LangGraph thread_id for multi-turn memory.
        image_dir: Optional per-session image directory for plots.

    Yields:
        Dict per message event from the agent stream.
    """
    agent = create_math_agent(config, image_dir=image_dir)
    graph_config: dict[str, Any] = {"configurable": {"thread_id": thread_id}}

    for chunk in agent.stream(
        {"messages": [HumanMessage(content=user_input)]},
        config=graph_config,
        stream_mode="updates",
    ):
        for node_name, state_update in chunk.items():
            if node_name not in ("model", "tools"):
                continue

            messages = state_update.get("messages", [])
            for msg in messages:
                type_name = type(msg).__name__

                event: dict[str, Any] = {
                    "node": node_name,
                    "type": type_name,
                }

                if type_name == "AIMessage":
                    # Handle string content
                    if isinstance(msg.content, str):
                        event["content"] = msg.content
                    # Handle list content (multimodal blocks)
                    elif isinstance(msg.content, list):
                        texts = []
                        for block in msg.content:
                            if isinstance(block, dict) and block.get("type") == "text":
                                texts.append(block.get("text", ""))
                        event["content"] = "\n".join(texts)
                    else:
                        event["content"] = str(msg.content)

                    # Include tool calls if present
                    if hasattr(msg, "tool_calls") and msg.tool_calls:
                        event["tool_calls"] = msg.tool_calls

                elif type_name == "ToolMessage":
                    event["content"] = str(msg.content)
                    event["tool_name"] = getattr(msg, "name", "unknown")

                # Only yield if there's meaningful content
                if event.get("content"):
                    yield event


# Cache the agent creation to avoid re-creating on every turn
_agent_cache: Optional[Any] = None
_agent_config_hash: Optional[int] = None
_agent_image_dir: str | None = None


def get_or_create_agent(config: Config, image_dir: str | None = None):
    """Get a cached agent instance, or create a new one.

    The agent is cached per config+image_dir to avoid re-creating it on every
    Streamlit rerun. The checkpointer (MemorySaver) maintains multi-turn
    memory across turns within the same session.
    """
    global _agent_cache, _agent_config_hash, _agent_image_dir

    config_hash = hash(config.model_dump_json() + (image_dir or ""))
    if _agent_cache is None or _agent_config_hash != config_hash or _agent_image_dir != image_dir:
        _agent_cache = create_math_agent(config, image_dir=image_dir)
        _agent_config_hash = config_hash
        _agent_image_dir = image_dir

    return _agent_cache


def run_agent_stream_cached(
    user_input: str,
    thread_id: str,
    config: Config,
    image_dir: str | None = None,
) -> Generator[dict[str, Any], None, None]:
    """Run agent stream with a cached agent instance.

    Same interface as run_agent_stream() but reuses the agent across calls.
    """
    agent = get_or_create_agent(config, image_dir=image_dir)
    graph_config: dict[str, Any] = {"configurable": {"thread_id": thread_id}}

    for chunk in agent.stream(
        {"messages": [HumanMessage(content=user_input)]},
        config=graph_config,
        stream_mode="updates",
    ):
        for node_name, state_update in chunk.items():
            if node_name not in ("model", "tools"):
                continue

            messages = state_update.get("messages", [])
            for msg in messages:
                type_name = type(msg).__name__
                event: dict[str, Any] = {"node": node_name, "type": type_name}

                if type_name == "AIMessage":
                    if isinstance(msg.content, str):
                        event["content"] = msg.content
                    elif isinstance(msg.content, list):
                        texts = [b.get("text", "") for b in msg.content if isinstance(b, dict) and b.get("type") == "text"]
                        event["content"] = "\n".join(texts)
                    else:
                        event["content"] = str(msg.content)

                    if hasattr(msg, "tool_calls") and msg.tool_calls:
                        event["tool_calls"] = msg.tool_calls

                elif type_name == "ToolMessage":
                    event["content"] = str(msg.content)
                    event["tool_name"] = getattr(msg, "name", "unknown")

                if event.get("content"):
                    yield event
