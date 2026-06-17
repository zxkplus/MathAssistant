# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Links
- [src/math_assistant/main.py](src/math_assistant/main.py) — CLI entry point and REPL loop
- [src/math_assistant/agent.py](src/math_assistant/agent.py) — Agent wiring (LLM + tools + middleware + checkpointer)
- [src/math_assistant/prompts.py](src/math_assistant/prompts.py) — System prompt and welcome message
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

**Agent pattern**: LangChain's `create_agent()` compiles a LangGraph state graph from an LLM (`ChatOpenAI` pointing at DeepSeek's API), two tools, middleware, a system prompt, and an `InMemorySaver` checkpointer for multi-turn conversation memory across a `thread_id`.

**Data flow**: `main.py` → `Config.load()` (YAML + env vars) → `create_math_agent(config)` → REPL loop that calls `agent.invoke({"messages": [HumanMessage(...)]})`, then extracts `AIMessage` and `ToolMessage` objects from the result and hands them to the UI layer.

**Tools** — two LangChain `@tool` functions, both registered in [agent.py:41](src/math_assistant/agent.py#L41):
1. **`execute_python`** (`src/math_assistant/tools/python_executor.py`) — writes the user's code plus a prologue (Agg backend, sympy/numpy/matplotlib imports) into a temp `.py` file and runs it via `subprocess.run` with a configurable timeout. Cleanup deletes the temp file.
2. **`web_search`** (`src/math_assistant/tools/search.py`) — delegates to a swappable `BaseSearchProvider`; currently only DuckDuckGo is implemented. The provider is set via a module-level global in the search tool module.

**Search providers** (`src/math_assistant/search_providers/`) — pluggable architecture: subclass `BaseSearchProvider`, implement `search()` and `name()`, then register in `PROVIDER_REGISTRY` in `__init__.py`.

**UI layer** (`src/math_assistant/ui/`) — `AbstractUI` defines the interface; `CLIUI` is the Rich-based terminal implementation. The agent logic never touches UI code directly — `main.py` bridges them. This decoupling allows swapping in a Gradio or Streamlit UI later.

**Configuration** (`src/math_assistant/config.py`) — Pydantic models with `Config.load()` reading `config.yaml` and then merging environment variable overrides (all prefixed `MATH_ASSISTANT_*`). API key resolution: checks `api.api_key` field, then `MATH_ASSISTANT_API_KEY`, `DEEPSEEK_API_KEY`, `OPENAI_API_KEY` env vars in `get_api_key()`.

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
