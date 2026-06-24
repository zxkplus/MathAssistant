"""Abstract base class for vision (image-to-text) providers.

To add a new vision provider (e.g., Claude Vision, local model):
1. Subclass BaseVisionProvider.
2. Implement image_to_text() and name().
3. Register in vision_providers/__init__.py PROVIDER_REGISTRY.
"""

from abc import ABC, abstractmethod


class BaseVisionProvider(ABC):
    """Abstract base for swappable vision / image-to-text providers."""

    @abstractmethod
    def image_to_text(self, image_path: str, prompt: str = "") -> str:
        """Extract text (especially math) from an image.

        Args:
            image_path: Path to the image file (PNG, JPG, etc.).
            prompt: Optional custom prompt to guide extraction.
                    If empty, a default math-focused prompt is used.

        Returns:
            Extracted text content as a string.
        """
        ...

    @abstractmethod
    def name(self) -> str:
        """Return a human-readable provider name for logging."""
        ...
