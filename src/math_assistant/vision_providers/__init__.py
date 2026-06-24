"""Vision provider registry.

To add a new provider:
1. Create a module with a class that implements BaseVisionProvider.
2. Add it to PROVIDER_REGISTRY below.
"""

from .base import BaseVisionProvider
from .openai_vision import OpenAIVisionProvider

PROVIDER_REGISTRY: dict[str, type[BaseVisionProvider]] = {
    "openai": OpenAIVisionProvider,
    # "claude": ClaudeVisionProvider,       # uncomment when added
    # "qwen_vl": QwenVLProvider,            # uncomment when added
    # "local": LocalVisionProvider,         # uncomment when added
}


def get_vision_provider(name: str, **kwargs) -> BaseVisionProvider:
    """Create a vision provider instance by name.

    Args:
        name: Provider name (e.g. "openai").
        **kwargs: Additional arguments passed to the provider constructor.

    Returns:
        A BaseVisionProvider instance.

    Raises:
        ValueError: If the provider name is not in PROVIDER_REGISTRY.
    """
    if name not in PROVIDER_REGISTRY:
        available = ", ".join(PROVIDER_REGISTRY.keys())
        raise ValueError(
            f"Unknown vision provider '{name}'. Available: {available}"
        )
    cls = PROVIDER_REGISTRY[name]
    return cls(**kwargs)
