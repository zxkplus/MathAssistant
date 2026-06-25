"""Baidu AI Search provider (百度AI搜索).

Uses Baidu Qianfan (千帆) AppBuilder's AI Search API, which is fully
accessible from mainland China without a VPN.

Sign up at https://console.bce.baidu.com/qianfan to get an API key.
Free tier: 100 queries/day.  Paid: ~0.036 RMB/query.

The AI Search endpoint uses an OpenAI-compatible chat-completions protocol,
which means it returns search-augmented responses.  We extract structured
web results from the response where possible.
"""

import json
import urllib.request
import urllib.error
from typing import Optional

from .base import BaseSearchProvider, SearchResult


# Baidu Qianfan AI Search endpoint (OpenAI-compatible chat completions)
BAIDU_AI_SEARCH_URL = "https://qianfan.baidubce.com/v2/ai_search/chat/completions"


class BaiduSearchProvider(BaseSearchProvider):
    """Baidu AI Search provider (China-accessible, 100 free queries/day)."""

    def __init__(self, api_key: Optional[str] = None):
        """Args:
            api_key: Baidu Qianfan API key (Bearer token).  If None, reads
                     MATH_ASSISTANT_BAIDU_API_KEY env var at search time.
        """
        self.api_key = api_key

    def name(self) -> str:
        return "Baidu AI Search"

    def _resolve_api_key(self) -> str:
        """Resolve API key: explicit > env var."""
        import os

        if self.api_key:
            return self.api_key
        env_key = os.environ.get("MATH_ASSISTANT_BAIDU_API_KEY", "")
        if env_key:
            return env_key
        raise ValueError(
            "Baidu API key not configured.  Set it in config.yaml:\n"
            "  search:\n"
            "    baidu_api_key: \"sk-xxx\"\n"
            "Or via environment variable: MATH_ASSISTANT_BAIDU_API_KEY"
        )

    def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        """Search via Baidu AI Search and return structured results.

        The Baidu AI Search endpoint returns an OpenAI-compatible chat
        completion with search-augmented content.  We send a prompt that
        asks for structured web results, then parse the response.
        """
        try:
            api_key = self._resolve_api_key()
        except ValueError as e:
            return [SearchResult(
                title="Configuration Error",
                url="",
                snippet=str(e),
            )]

        # Build a prompt that elicits search results from the AI Search engine.
        # The Baidu AI Search model automatically performs a web search when
        # asked a question — we frame the query to maximise result quality.
        search_prompt = (
            f'请搜索以下数学问题，并列出最权威的 {max_results} 个网页结果。'
            f'对每个结果，请提供：标题、URL、摘要。\n\n'
            f'搜索内容：{query}'
        )

        payload = json.dumps({
            "messages": [
                {"role": "user", "content": search_prompt},
            ],
            "stream": False,
        }).encode("utf-8")

        req = urllib.request.Request(
            BAIDU_AI_SEARCH_URL,
            data=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
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
                    f"Baidu API returned HTTP {e.code}. {error_body}".strip()
                ),
            )]
        except Exception as e:
            return [SearchResult(
                title="Search Error",
                url="",
                snippet=f"Baidu request failed: {str(e)}",
            )]

        # Parse the OpenAI-compatible response
        results: list[SearchResult] = []

        try:
            choices = body.get("choices", [])
            if not choices:
                return [SearchResult(
                    title="No Results",
                    url="",
                    snippet="Baidu AI Search returned an empty response.",
                )]

            content = choices[0].get("message", {}).get("content", "")

            if not content:
                return [SearchResult(
                    title="No Results",
                    url="",
                    snippet="Baidu AI Search returned empty content.",
                )]

            # The response is free-text augmented with search.  We return the
            # full response as a single rich result so the LLM can read it.
            # For structured extraction, we look for URLs in the text.
            results.append(SearchResult(
                title=f"Baidu AI Search: {query[:80]}",
                url=BAIDU_AI_SEARCH_URL,
                snippet=content.strip(),
            ))

            # If the response contains explicit structured results with URLs,
            # also extract them as individual results for the agent.
            # This is a heuristic — the AI Search response format varies.
            self._extract_url_mentions(content, results)

        except Exception as e:
            return [SearchResult(
                title="Parse Error",
                url="",
                snippet=f"Failed to parse Baidu response: {str(e)}",
            )]

        return results

    @staticmethod
    def _extract_url_mentions(content: str, results: list[SearchResult]) -> None:
        """Attempt to extract URLs and their surrounding context from the
        AI-generated response text.

        This is a best-effort extraction — the Baidu AI Search response is
        free-form text, not structured search results.
        """
        import re

        # Find http/https URLs in the content
        url_pattern = re.compile(r'(https?://[^\s\)\]】，。\n]+)')
        urls = url_pattern.findall(content)

        # If we already have the main result, skip adding duplicates
        existing_urls = {r["url"] for r in results if r["url"]}
        new_urls = [u for u in urls if u not in existing_urls]

        for url in new_urls[:5]:
            results.append(SearchResult(
                title="Related Source",
                url=url,
                snippet="(Refer to the main Baidu AI Search response for context.)",
            ))
