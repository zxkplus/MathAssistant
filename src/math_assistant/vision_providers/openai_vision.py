"""OpenAI-compatible Vision provider.

Sends an image as a base64 data URI to any OpenAI-compatible multimodal API
(GPT-4V, GPT-4o, DeepSeek-VL2, Qwen-VL, local vLLM, etc.).

Uses httpx for the HTTP call so it is independent of the ChatOpenAI client
used for the main agent — allowing different base URLs and models.
"""

import base64
import mimetypes
from typing import Optional

import httpx

from .base import BaseVisionProvider

DEFAULT_MATH_PROMPT = """Please look at this image carefully. It contains a math problem (possibly handwritten or printed).

Extract the ENTIRE math problem as accurately as possible. Output it in a clean, well-formatted text form using LaTeX notation for mathematical expressions (surround inline math with $...$ and display math with $$...$$).

Rules:
- Preserve ALL numbers, symbols, operators, and structure exactly.
- If there are multiple parts (a, b, c, etc.), extract all of them.
- If there are diagrams or geometric figures, describe them in words inside [brackets].
- If there are multiple-choice options, list them all.
- Do NOT solve the problem — only transcribe it.
- Output only the extracted text, no commentary."""


class OpenAIVisionProvider(BaseVisionProvider):
    """Vision provider using any OpenAI-compatible multimodal API."""

    def __init__(
        self,
        model: str = "gpt-4o",
        api_key: Optional[str] = None,
        base_url: str = "https://api.openai.com/v1",
        prompt: str = "",
        max_tokens: int = 4096,
        temperature: float = 0.0,
        timeout: float = 60.0,
    ):
        """Initialize the OpenAI-compatible vision provider.

        Args:
            model: Multimodal model name (gpt-4o, deepseek-vl2, qwen-vl-max, etc.).
            api_key: API key. Falls back to same env vars as Config.get_api_key().
            base_url: API base URL (must end with /v1 for OpenAI-compatible endpoints).
            prompt: Custom extraction prompt (uses DEFAULT_MATH_PROMPT if empty).
            max_tokens: Maximum tokens in the response.
            temperature: Sampling temperature (0.0 = deterministic).
            timeout: HTTP request timeout in seconds.
        """
        self._model = model
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._custom_prompt = prompt
        self._max_tokens = max_tokens
        self._temperature = temperature
        self._timeout = timeout

    def name(self) -> str:
        return f"OpenAIVision({self._model})"

    def image_to_text(self, image_path: str, prompt: str = "") -> str:
        """Send an image to the VLM and return the extracted text.

        Args:
            image_path: Path to the image file.
            prompt: Optional custom prompt (overrides the constructor prompt).

        Returns:
            Extracted text content.
        """
        # Read and encode the image
        try:
            with open(image_path, "rb") as f:
                image_data = f.read()
        except FileNotFoundError:
            return f"Error: Image file not found at '{image_path}'."
        except Exception as e:
            return f"Error: Could not read image file '{image_path}': {e}"

        # Detect MIME type
        mime_type, _ = mimetypes.guess_type(image_path)
        if mime_type is None or not mime_type.startswith("image/"):
            mime_type = "image/png"  # fallback

        # Encode as base64 data URI
        encoded = base64.b64encode(image_data).decode("utf-8")
        data_uri = f"data:{mime_type};base64,{encoded}"

        # Determine the extraction prompt
        extraction_prompt = prompt or self._custom_prompt or DEFAULT_MATH_PROMPT

        # Resolve API key
        api_key = self._api_key
        if api_key is None:
            import os
            for env_var in ("MATH_ASSISTANT_API_KEY", "DEEPSEEK_API_KEY", "OPENAI_API_KEY"):
                api_key = os.environ.get(env_var)
                if api_key:
                    break
        if api_key is None:
            return (
                "Error: No API key configured for the vision provider. "
                "Set it in config.yaml under vision.api_key, "
                "or via DEEPSEEK_API_KEY / OPENAI_API_KEY environment variable."
            )

        # Build the request
        url = f"{self._base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": extraction_prompt},
                        {"type": "image_url", "image_url": {"url": data_uri}},
                    ],
                }
            ],
            "max_tokens": self._max_tokens,
            "temperature": self._temperature,
        }

        # Send the request
        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as e:
            return f"Error: Vision API returned HTTP {e.response.status_code}: {e.response.text[:500]}"
        except httpx.RequestError as e:
            return f"Error: Could not connect to vision API at {url}: {e}"
        except Exception as e:
            return f"Error: Unexpected error during vision API call: {e}"

        # Extract the response text
        try:
            content = data["choices"][0]["message"]["content"]
            return content.strip()
        except (KeyError, IndexError, TypeError) as e:
            return f"Error: Unexpected response format from vision API: {e}\nRaw: {str(data)[:500]}"
