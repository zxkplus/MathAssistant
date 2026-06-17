"""Web search tool for MathAssistant.

Creates a LangChain tool that delegates to a swappable search provider.
"""

from langchain.tools import tool
from pydantic import BaseModel, Field

from ..search_providers.base import BaseSearchProvider

# Module-level reference to the active search provider.
# Set by create_search_tool().
_current_provider: BaseSearchProvider | None = None


class SearchInput(BaseModel):
    query: str = Field(description="The search query string.")
    num_results: int = Field(
        default=5,
        description="Number of search results to return (1-10).",
    )


@tool(args_schema=SearchInput)
def web_search(query: str, num_results: int = 5) -> str:
    """Search the web for math theories, definitions, theorems, and authoritative sources.

    Use this tool to:
    - Look up precise definitions of math concepts
    - Find authoritative sources for theorems and formulas
    - Research mathematical topics you need more information about
    - Verify mathematical claims with external sources

    Returns formatted search results with title, URL, and snippet.
    """
    global _current_provider
    if _current_provider is None:
        return "Search is not configured. Please set up a search provider."

    results = _current_provider.search(query, max_results=num_results)

    if not results:
        return f"No results found for: {query}"

    lines = [f"Search results for: **{query}**\n"]
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. **{r['title']}**")
        lines.append(f"   URL: {r['url']}")
        lines.append(f"   {r['snippet']}")
        lines.append("")

    return "\n".join(lines)


def create_search_tool(provider: BaseSearchProvider):
    """Configure the web_search tool to use the given search provider.

    Args:
        provider: A BaseSearchProvider instance.

    Returns:
        The configured web_search tool function.
    """
    global _current_provider
    _current_provider = provider
    return web_search
