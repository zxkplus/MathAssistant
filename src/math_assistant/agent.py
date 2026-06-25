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
from .tools.python_executor import execute_python
from .tools.search import create_search_tool
from .tools.image_to_text import create_image_to_text_tool


def create_math_agent(config: Config):
    """Build and return the MathAssistant agent.

    Each tool/role uses its own LLM profile from config:
      - main agent (chat)  → config.main   (e.g. DeepSeek)
      - image-to-text tool → config.vision (e.g. Kimi)

    Args:
        config: Validated application configuration.

    Returns:
        A compiled LangGraph state graph ready for invocation.
    """
    # Main agent LLM — uses the "main" profile
    llm = config.main.create_chat_openai(role_name="main")

    # Set up the search provider
    search_provider = get_search_provider(config.search.provider)
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
