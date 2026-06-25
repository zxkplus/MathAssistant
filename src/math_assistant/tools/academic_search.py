"""Academic paper search tool for MathAssistant.

Provides a LangChain tool that searches academic paper databases
(Semantic Scholar, arXiv via DeepXiv) for mathematical research.

Semantic Scholar is free and mostly accessible from China without a VPN.
DeepXiv (by Beijing BAAI) is a China-specific alternative for arXiv access.
"""

import json
import urllib.request
import urllib.error
import urllib.parse

from langchain.tools import tool
from pydantic import BaseModel, Field


# ── API endpoints ─────────────────────────────────────────────────────────

SEMANTIC_SCHOLAR_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
# DeepXiv (智源 BAAI) — China-friendly arXiv access
DEEPXIV_SEARCH_URL = "https://data.rag.ac.cn/api/v1/search"


# ── Input schema ──────────────────────────────────────────────────────────

class PaperSearchInput(BaseModel):
    query: str = Field(
        description="The search query for academic papers (e.g. 'Riemann hypothesis proof', 'topological data analysis')."
    )
    max_results: int = Field(
        default=5,
        description="Number of papers to return (1-10).",
    )


# ── Tool ──────────────────────────────────────────────────────────────────

@tool(args_schema=PaperSearchInput)
def search_papers(query: str, max_results: int = 5) -> str:
    """Search academic papers (Semantic Scholar, arXiv) for mathematical research.

    Use this tool when you need:
    - Authoritative mathematical references and research papers
    - Formal proofs, theorems, and mathematical results from academic literature
    - Recent research developments in mathematics
    - Citations and academic sources for mathematical claims

    This tool searches peer-reviewed papers, preprints, and conference
    proceedings — much more authoritative than general web search for
    mathematical content.

    Returns formatted paper results with title, authors, year, abstract, and URL.
    """
    limit = max(1, min(max_results, 10))
    papers = _search_semantic_scholar(query, limit)

    if not papers:
        # Fall back to DeepXiv for China accessibility
        papers = _search_deepxiv(query, limit)

    if not papers:
        return f"No academic papers found for: **{query}**\n\nTry a broader or different query."

    lines = [f"📚 **Academic papers for: {query}**\n"]
    for i, p in enumerate(papers, 1):
        title = p.get("title", "Untitled")
        authors = p.get("authors", "Unknown")
        year = p.get("year", "n.d.")
        abstract = p.get("abstract", "No abstract available.")
        url = p.get("url", "")

        # Truncate abstract for readability
        if len(abstract) > 300:
            abstract = abstract[:297] + "..."

        lines.append(f"{i}. **{title}**")
        lines.append(f"   Authors: {authors} ({year})")
        lines.append(f"   {abstract}")
        if url:
            lines.append(f"   URL: {url}")
        lines.append("")

    return "\n".join(lines)


# ── Internal helpers ──────────────────────────────────────────────────────

def _search_semantic_scholar(query: str, limit: int) -> list[dict]:
    """Search Semantic Scholar for papers.

    Semantic Scholar is free, requires no API key for basic usage
    (rate limit: 100 requests per 5 minutes without key, higher with key).
    """
    params = urllib.parse.urlencode({
        "query": query,
        "limit": limit,
        "fields": "title,url,abstract,year,authors,externalIds",
    })
    url = f"{SEMANTIC_SCHOLAR_URL}?{params}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "MathAssistant/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.HTTPError, urllib.error.URLError, Exception):
        return []

    papers: list[dict] = []
    for item in body.get("data", []):
        # Format authors
        author_names = [
            a.get("name", "")
            for a in item.get("authors", [])
        ]
        authors = ", ".join(author_names[:5])
        if len(author_names) > 5:
            authors += f" et al."

        # Resolve URL
        url = ""
        ext_ids = item.get("externalIds", {}) or {}
        if ext_ids.get("DOI"):
            url = f"https://doi.org/{ext_ids['DOI']}"
        elif item.get("url"):
            url = item["url"]
        elif ext_ids.get("ArXiv"):
            url = f"https://arxiv.org/abs/{ext_ids['ArXiv']}"

        papers.append({
            "title": item.get("title", "Untitled"),
            "authors": authors,
            "year": str(item.get("year", "")),
            "abstract": item.get("abstract") or "Abstract not available.",
            "url": url,
        })

    return papers


def _search_deepxiv(query: str, limit: int) -> list[dict]:
    """Search DeepXiv (智源 BAAI) for papers — China-friendly fallback.

    DeepXiv is developed by Beijing Academy of AI (BAAI) specifically for
    Chinese AI agents.  Covers 200M+ open-access papers.
    """
    payload = json.dumps({
        "query": query,
        "max_results": limit,
    }).encode("utf-8")

    try:
        req = urllib.request.Request(
            DEEPXIV_SEARCH_URL,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "MathAssistant/1.0",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.HTTPError, urllib.error.URLError, Exception):
        return []

    papers: list[dict] = []
    results = body.get("results") or body.get("data") or []
    for item in results[:limit]:
        papers.append({
            "title": item.get("title", "Untitled"),
            "authors": item.get("authors", "Unknown"),
            "year": str(item.get("year", "")),
            "abstract": item.get("abstract") or item.get("snippet", "Abstract not available."),
            "url": item.get("url", ""),
        })

    return papers
