"""Agent orchestrator for MathAssistant.

Wires together the LLM, tools, middleware, and checkpointer into
a compiled LangGraph state graph using LangChain's create_agent().
"""

from langchain.agents.factory import create_agent
from langchain.agents.middleware import ToolCallLimitMiddleware
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI

from .config import Config
from .prompts import SYSTEM_PROMPT
from .search_providers import get_search_provider
from .vision_providers import get_vision_provider
from .tools.python_executor import execute_python
from .tools.search import create_search_tool
from .tools.image_to_text import create_image_to_text_tool


def create_math_agent(config: Config):
    """Build and return the MathAssistant agent.

    Args:
        config: Validated application configuration.

    Returns:
        A compiled LangGraph state graph ready for invocation.
    """
    # Create the LLM (DeepSeek via OpenAI-compatible API)
    llm = ChatOpenAI(
        model=config.model.name,
        api_key=config.get_api_key(),
        base_url=config.api.base_url,
        temperature=config.model.temperature,
    )

    # Set up the search provider
    search_provider = get_search_provider(config.search.provider)
    search_tool = create_search_tool(search_provider)

    # Set up the vision (image-to-text) provider
    # API key: use vision-specific key, or fall back to the main API key
    vision_api_key = config.vision.api_key or config.get_api_key()
    # Base URL: if vision.base_url is still the default (OpenAI) but main API
    # is using a different provider (e.g. DeepSeek), follow the main base URL
    # so the same API key works for both.
    vision_base_url = config.vision.base_url
    if vision_base_url == "https://api.openai.com/v1" and config.api.base_url != "https://api.openai.com/v1":
        vision_base_url = config.api.base_url
    vision_provider = get_vision_provider(
        config.vision.provider,
        model=config.vision.model,
        api_key=vision_api_key,
        base_url=vision_base_url,
    )
    image_to_text_tool = create_image_to_text_tool(vision_provider)

    # Build tool list
    tools = [search_tool, execute_python, image_to_text_tool]

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
