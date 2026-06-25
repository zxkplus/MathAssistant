"""MathAssistant Streamlit Frontend — Main Entry Point.

Usage:
    streamlit run src/math_assistant/frontend/app.py

Requires the FastAPI backend to be running for auth, persistence,
auto-tagging, and analytics. The agent (LLM + tools) runs directly
in this process via create_math_agent().
"""

import sys

import streamlit as st

# Page config must be the first Streamlit call
st.set_page_config(
    page_title="MathAssistant",
    page_icon="🧮",
    layout="wide",
    initial_sidebar_state="expanded",
)

from math_assistant.config import Config
from math_assistant.workspace import WorkspaceManager, WorkspaceContext
from math_assistant.frontend import session_store as store
from math_assistant.frontend.auth_page import render_auth_page
from math_assistant.frontend.chat_page import render_chat_page
from math_assistant.frontend.sidebar import render_sidebar


def _load_config() -> Config:
    """Load the main application config for agent creation.

    Returns cached config stored in session_state if available,
    otherwise loads from YAML and environment variables.
    """
    if store.Keys.CONFIG in st.session_state and st.session_state[store.Keys.CONFIG] is not None:
        return st.session_state[store.Keys.CONFIG]

    config = Config.load()
    try:
        config.get_api_key()
    except ValueError:
        # API key not configured — will be checked at agent run time
        pass

    st.session_state[store.Keys.CONFIG] = config
    return config


def _init_workspace(config: Config) -> None:
    """Ensure workspace manager and context are initialized in session state.

    Creates a new workspace directory for the current session on first load.
    On subsequent reruns the workspace context persists in session_state.
    """
    # Initialize workspace manager (once per session)
    if store.get_workspace_mgr() is None:
        mgr = WorkspaceManager(config.output.workspace_root)
        store.set_workspace_mgr(mgr)

    # Initialize workspace context (once per session)
    if store.get_workspace_ctx() is None:
        mgr = store.get_workspace_mgr()
        if mgr is not None:
            thread_id = store.get_thread_id()
            ctx = mgr.create_workspace(
                session_id=thread_id,
                model=config.main.model,
            )
            store.set_workspace_ctx(ctx)


def main() -> None:
    """Main app entry point. Routes between auth page and chat page."""
    # Initialize session state
    store.init_session_state()

    # Load config
    config = _load_config()

    # Initialize workspace (after config is loaded, before rendering)
    _init_workspace(config)

    # Check auth state
    if not store.is_logged_in():
        render_auth_page()
        return

    # Authenticated — show main chat interface
    render_sidebar()
    render_chat_page(config)


if __name__ == "__main__":
    main()
