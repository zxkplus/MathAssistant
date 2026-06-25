# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Links
- [src/math_assistant/main.py](src/math_assistant/main.py) — CLI entry point and REPL loop
- [src/math_assistant/agent.py](src/math_assistant/agent.py) — Agent wiring (LLM + tools + middleware + checkpointer)
- [src/math_assistant/prompts.py](src/math_assistant/prompts.py) — System prompt and welcome message
- [src/math_assistant/config.py](src/math_assistant/config.py) — Configuration (LLMProfile pattern, layered loading)
- [src/math_assistant/workspace/](src/math_assistant/workspace/) — Workspace-based session management
- [config.yaml](config.yaml) — Default configuration

## Running the App

```bash
# Set your API key (DEEPSEEK_API_KEY, MATH_ASSISTANT_API_KEY, or OPENAI_API_KEY)
export DEEPSEEK_API_KEY=sk-xxx

# Launch
python run.py

# With overrides
python run.py --api-key sk-xxx --model deepseek-chat

# Interactive commands during REPL:
#   quit / exit / q  — exit
#   new / reset / clear — start a fresh conversation session
```

There are no tests, no linter, and no build step in this project.

## Architecture

**Agent pattern**: LangChain's `create_agent()` compiles a LangGraph state graph from an LLM (`ChatOpenAI` pointing at DeepSeek's API), four tools, middleware, a system prompt, and an `InMemorySaver` checkpointer for multi-turn conversation memory across a `thread_id`.

**Data flow**: `main.py` → `Config.load()` (YAML + env vars) → `create_math_agent(config, image_dir=...)` → REPL loop that calls `agent.stream({"messages": [HumanMessage(...)]})`, then extracts `AIMessage` and `ToolMessage` objects from the result and hands them to the UI layer. The REPL loop now integrates `WorkspaceManager` for session-scoped file management.

**Tools** — four LangChain `@tool` functions, registered in [agent.py:60-63](src/math_assistant/agent.py#L60-L63):
1. **`execute_python`** (`src/math_assistant/tools/python_executor.py`) — factory pattern via `create_python_executor(image_dir, timeout_seconds)` that returns a configured tool. Writes user code plus a prologue (Agg backend, CJK font detection, sympy/numpy/matplotlib imports) into a temp `.py` file and runs it via `subprocess.run` with a configurable timeout. Runs from the workspace directory so relative `images/` paths land in the session workspace. Auto-prints bare expressions, fixes unicode escape issues in triple-quoted strings. Cleanup deletes the temp file.
2. **`web_search`** (`src/math_assistant/tools/search.py`) — delegates to a swappable `BaseSearchProvider`; supports DuckDuckGo, Baidu AI Search, and Bocha AI Search. The provider is set via a module-level global in the search tool module.
3. **`image_to_text`** (`src/math_assistant/tools/image_to_text.py`) — OCR for images containing math problems, using a separate vision LLM profile (default: Kimi/Moonshot).
4. **`search_papers`** (`src/math_assistant/tools/academic_search.py`) — searches academic papers via Semantic Scholar (free) with DeepXiv (智源BAAI) as China-friendly fallback. Returns formatted paper results with title, authors, year, abstract, and URL. Enabled by `search.academic_search: true` in config.

**Search providers** (`src/math_assistant/search_providers/`) — pluggable architecture: subclass `BaseSearchProvider`, implement `search()` and `name()`, then register in `PROVIDER_REGISTRY` in `__init__.py`. Three providers registered:
- `duckduckgo` — free, but blocked in mainland China (requires VPN)
- `baidu` — Baidu AI Search (百度AI搜索), 100 free queries/day
- `bocha` — Bocha AI Search (博查), 2,000 free queries on signup

**Workspace management** (`src/math_assistant/workspace/`) — each session gets a self-contained directory under `workspace_root`:
- `WorkspaceManager` — creates, lists, deletes per-session workspace directories named `{date}-{id8}-{slug}/`
- `WorkspaceContext` — immutable value object holding all paths: `workspace_dir`, `images_dir`, `session_json_path`, `session_md_path`, `session_html_path`
- `WorkspaceIndex` — JSON index (`index.json`) cataloguing all sessions with atomic writes and cross-platform advisory file locks; can be rebuilt from directory scan
- Workspaces are the **primary** session storage; legacy `save_dir`/`image_dir` paths are kept for backward compatibility

**Session serialization** (`src/math_assistant/session/recorder.py`) — all data classes (`Session`, `Turn`, `ToolCallRecord`, `QuestionGroup`) have `to_dict()` / `from_dict()` for JSON round-tripping. Top-level `serialize_session()` / `deserialize_session()` write/read `session.json` with atomic temp-file writes.

**UI layer** (`src/math_assistant/ui/`) — `AbstractUI` defines the interface; `CLIUI` is the Rich-based terminal implementation. The agent logic never touches UI code directly — `main.py` bridges them. This decoupling allows swapping in a Gradio or Streamlit UI later.

**Configuration** (`src/math_assistant/config.py`) — Pydantic models with `Config.load()` reading `config.yaml` and then merging environment variable overrides (all prefixed `MATH_ASSISTANT_*`). Uses the **LLMProfile pattern**: each role (`main`, `vision`, future sub-agents) gets its own self-contained `LLMProfile` with independent `model`, `api_key`, and `base_url` — no cross-role fallbacks. Legacy `model`/`api`/`vision` config sections are auto-migrated on load.

**Middleware**: `ToolCallLimitMiddleware` caps agent tool calls per turn (default 20, configurable via `agent.max_tool_calls`).

## Key Dependencies

- `langchain` + `langchain-openai` — agent framework, LLM client (OpenAI-compatible protocol)
- `sympy` — symbolic math (solve, diff, integrate, simplify, matrix ops)
- `numpy` — numerical computation
- `matplotlib` — chart generation (Agg backend, headless-safe)
- `duckduckgo-search` — free web search (no API key needed)
- `rich` — terminal formatting (Markdown rendering, panels, colors)
- `pydantic` — config models and tool input schemas
- `pyyaml` — YAML config parsing
