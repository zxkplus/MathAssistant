"""Bocha AI Search provider.

Bocha (博查) is a China-accessible search API that powers a significant
portion of DeepSeek's real-time search traffic.  No VPN required.

API docs: https://open.bochaai.com

Sign up at https://open.bochaai.com to get a free API key (2,000 free
queries on registration).
"""

import json
import urllib.request
import urllib.error
from typing import Optional

from .base import BaseSearchProvider, SearchResult


BOCHA_API_URL = "https://api.bochaai.com/v1/ai/search"


class BochaSearchProvider(BaseSearchProvider):
    """Bocha AI-powered web search (China-accessible, freemium)."""

    def __init__(self, api_key: Optional[str] = None):
        """Args:
            api_key: Bocha API key.  If None, reads MATH_ASSISTANT_BOCHA_API_KEY
                     env var at search time.
        """
        self.api_key = api_key

    def name(self) -> str:
        return "Bocha"

    def _resolve_api_key(self) -> str:
        """Resolve API key: explicit > env var."""
        import os

        if self.api_key:
            return self.api_key
        env_key = os.environ.get("MATH_ASSISTANT_BOCHA_API_KEY", "")
        if env_key:
            return env_key
        raise ValueError(
            "Bocha API key not configured.  Set it in config.yaml:\n"
            "  search:\n"
            "    bocha_api_key: \"sk-xxx\"\n"
            "Or via environment variable: MATH_ASSISTANT_BOCHA_API_KEY"
        )

    def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        """Search Bocha and return structured results."""
        try:
            api_key = self._resolve_api_key()
        except ValueError as e:
            return [SearchResult(
                title="Configuration Error",
                url="",
                snippet=str(e),
            )]

        # Clamp max_results to Bocha's allowed range (1-20)
        count = max(1, min(max_results, 20))

        payload = json.dumps({
            "query": query,
            "count": count,
        }).encode("utf-8")

        req = urllib.request.Request(
            BOCHA_API_URL,
            data=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            error_body = ""
            try:
                error_body = e.read().decode("utf-8")[:200]
            except Exception:
                pass
            return [SearchResult(
                title="Search Error",
                url="",
                snippet=(
                    f"Bocha API returned HTTP {e.code}. {error_body}".strip()
                ),
            )]
        except Exception as e:
            return [SearchResult(
                title="Search Error",
                url="",
                snippet=f"Bocha request failed: {str(e)}",
            )]

        # Parse Bocha response
        # Expected shape: {"code": 200, "data": {"results": [{"title":..., "url":..., "snippet":...}]}}
        results: list[SearchResult] = []

        try:
            # Bocha wraps results in data.results or data.documents depending on
            # the API version.  Handle both shapes.
            data = body.get("data", body)
            items = data.get("results") or data.get("documents") or data.get("items") or []

            # Fallback: if the top-level already has a list of results
            if not items and isinstance(body, dict):
                # Some versions return {"code": 200, "results": [...]}
                items = body.get("results") or body.get("documents") or []

            for item in items:
                results.append(SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("snippet") or item.get("content") or item.get("description", ""),
                ))
        except Exception as e:
            return [SearchResult(
                title="Parse Error",
                url="",
                snippet=f"Failed to parse Bocha response: {str(e)}",
            )]

        return results
