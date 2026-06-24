"""Image-to-text tool for MathAssistant.

Creates a LangChain tool that delegates to a swappable vision provider
for extracting math problems from images.
"""

from langchain.tools import tool
from pydantic import BaseModel, Field

from ..vision_providers.base import BaseVisionProvider

# Module-level reference to the active vision provider.
# Set by create_image_to_text_tool().
_current_provider: BaseVisionProvider | None = None


class ImageToTextInput(BaseModel):
    image_path: str = Field(
        description="Path to the image file (PNG, JPG, etc.) containing the math problem to extract."
    )
    custom_prompt: str = Field(
        default="",
        description="Optional custom instruction for extraction (e.g., 'focus on the equations only'). "
                    "Leave empty to use the default math-focused prompt.",
    )


@tool(args_schema=ImageToTextInput)
def image_to_text(image_path: str, custom_prompt: str = "") -> str:
    """Extract math problems from an image and convert them to accurate text.

    Use this tool when a student provides an image file path containing a math problem.
    The image can be a photo of handwritten work, a screenshot, a scanned textbook page,
    or any image that contains mathematical content.

    This tool uses a vision AI model to "read" the image and transcribe all math
    expressions, numbers, symbols, and text into properly formatted output with
    LaTeX notation for mathematical expressions.

    After extraction, you should:
    - Read the extracted text carefully
    - Confirm with the student that the transcription is correct
    - Then proceed to solve or explain the problem
    """
    global _current_provider
    if _current_provider is None:
        return (
            "Image-to-text is not configured. Please set up a vision provider "
            "in config.yaml (vision section)."
        )

    result = _current_provider.image_to_text(
        image_path=image_path,
        prompt=custom_prompt if custom_prompt else "",
    )

    if result.startswith("Error:"):
        return result

    return f"[Extracted from '{image_path}']\n\n{result}"


def create_image_to_text_tool(provider: BaseVisionProvider):
    """Configure the image_to_text tool to use the given vision provider.

    Args:
        provider: A BaseVisionProvider instance.

    Returns:
        The configured image_to_text tool function.
    """
    global _current_provider
    _current_provider = provider
    return image_to_text
