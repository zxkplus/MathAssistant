"""Agent orchestrator for MathAssistant.

Wires together the LLM, tools, middleware, and checkpointer into
a compiled LangGraph state graph using LangChain's create_agent().
"""

from langchain.agents.factory import create_agent
from langchain.agents.middleware import ToolCallLimitMiddleware
from langgraph.checkpoint.memory import MemorySaver

from .config import Config
from .prompts import SYSTEM_PROMPT
from .search_providers import get_search_provider
from .vision_providers import get_vision_provider
from .tools.python_executor import create_python_executor
from .tools.search import create_search_tool
from .tools.image_to_text import create_image_to_text_tool
from .tools.academic_search import search_papers


def create_math_agent(config: Config, image_dir: str | None = None):
    """Build and return the MathAssistant agent.

    Each tool/role uses its own LLM profile from config:
      - main agent (chat)  → config.main   (e.g. DeepSeek)
      - image-to-text tool → config.vision (e.g. Kimi)

    Args:
        config: Validated application configuration.
        image_dir: Optional per-session image directory for generated plots.
                   If None, uses config.output.image_dir (global fallback).

    Returns:
        A compiled LangGraph state graph ready for invocation.
    """
    # Main agent LLM — uses the "main" profile
    llm = config.main.create_chat_openai(role_name="main")

    # Set up the search provider — pass provider-specific API keys from config
    provider_kwargs = _build_provider_kwargs(config)
    search_provider = get_search_provider(config.search.provider, **provider_kwargs)
    search_tool = create_search_tool(search_provider)

    # Set up the vision (image-to-text) provider — uses the "vision" profile
    # Each profile is independent: vision has its own model + api_key + base_url
    vision_provider = get_vision_provider(
        "openai",  # Kimi is OpenAI-compatible — uses the same provider class
        model=config.vision.model,
        api_key=config.vision.api_key,
        base_url=config.vision.base_url,
    )
    image_to_text_tool = create_image_to_text_tool(vision_provider)

    # Set up python executor with session-specific image directory
    python_tool = create_python_executor(
        image_dir=image_dir or config.output.image_dir,
        timeout_seconds=config.python_executor.timeout_seconds,
    )

    # Build tool list — optionally include academic paper search
    tools = [search_tool, python_tool, image_to_text_tool]
    if config.search.academic_search:
        tools.append(search_papers)

    # Build middleware
    middleware = [
        ToolCallLimitMiddleware(run_limit=config.agent.max_tool_calls),
    ]

    # Create checkpointer for multi-turn conversation memory
    checkpointer = MemorySaver()

    # Create the agent
    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
        middleware=middleware,
        checkpointer=checkpointer,
    )

    return agent


def _build_provider_kwargs(config: Config) -> dict:
    """Build provider-specific keyword arguments from config.

    Only passes API keys that are actually configured (non-empty).
    DuckDuckGo ignores these; Baidu and Bocha use them.
    """
    kwargs: dict = {}

    if config.search.baidu_api_key:
        kwargs["api_key"] = config.search.baidu_api_key
    elif config.search.bocha_api_key:
        kwargs["api_key"] = config.search.bocha_api_key

    return kwargs
