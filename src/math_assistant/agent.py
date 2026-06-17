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
from .tools.python_executor import execute_python
from .tools.search import create_search_tool


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

    # Build tool list
    tools = [search_tool, execute_python]

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
