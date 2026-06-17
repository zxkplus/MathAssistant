"""Abstract base class for search providers.

To add a new search provider (e.g., Tavily, SerpAPI, Google):
1. Subclass BaseSearchProvider.
2. Implement search() and name().
3. Register in search_providers/__init__.py PROVIDER_REGISTRY.
"""

from abc import ABC, abstractmethod
from typing import TypedDict


class SearchResult(TypedDict):
    title: str
    url: str
    snippet: str


class BaseSearchProvider(ABC):
    """Abstract base for swappable web search providers."""

    @abstractmethod
    def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        """Execute a web search and return structured results."""
        ...

    @abstractmethod
    def name(self) -> str:
        """Return a human-readable provider name for logging."""
        ...
