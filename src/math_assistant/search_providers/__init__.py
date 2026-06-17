"""Search provider registry.

To add a new provider:
1. Create a module with a class that implements BaseSearchProvider.
2. Add it to PROVIDER_REGISTRY below.
"""

from .base import BaseSearchProvider
from .duckduckgo import DuckDuckGoSearchProvider

PROVIDER_REGISTRY: dict[str, type[BaseSearchProvider]] = {
    "duckduckgo": DuckDuckGoSearchProvider,
    # "tavily": TavilySearchProvider,       # uncomment when added
    # "serpapi": SerpAPISearchProvider,     # uncomment when added
    # "google": GoogleSearchProvider,       # uncomment when added
}


def get_search_provider(name: str, **kwargs) -> BaseSearchProvider:
    """Create a search provider instance by name.

    Args:
        name: Provider name (e.g. "duckduckgo", "tavily").
        **kwargs: Additional arguments passed to the provider constructor.

    Returns:
        A BaseSearchProvider instance.

    Raises:
        ValueError: If the provider name is not in PROVIDER_REGISTRY.
    """
    if name not in PROVIDER_REGISTRY:
        available = ", ".join(PROVIDER_REGISTRY.keys())
        raise ValueError(f"Unknown search provider '{name}'. Available: {available}")
    cls = PROVIDER_REGISTRY[name]
    return cls(**kwargs)
