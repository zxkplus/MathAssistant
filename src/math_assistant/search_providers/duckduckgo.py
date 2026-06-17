"""DuckDuckGo search provider using the duckduckgo_search library.

This provider requires no API key and is suitable for free usage.
"""

from .base import BaseSearchProvider, SearchResult


class DuckDuckGoSearchProvider(BaseSearchProvider):
    """DuckDuckGo-based web search (free, no API key required)."""

    def __init__(self, region: str = "wt-wt", safesearch: str = "moderate"):
        self.region = region
        self.safesearch = safesearch

    def name(self) -> str:
        return "DuckDuckGo"

    def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        """Search DuckDuckGo and return structured results."""
        from duckduckgo_search import DDGS

        results: list[SearchResult] = []
        try:
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=max_results):
                    results.append(SearchResult(
                        title=r.get("title", ""),
                        url=r.get("href", ""),
                        snippet=r.get("body", ""),
                    ))
        except Exception as e:
            # Return an error result so the agent knows the search failed
            results.append(SearchResult(
                title="Search Error",
                url="",
                snippet=f"Search failed: {str(e)}. Please try a different query.",
            ))
        return results
