"""Streamlit session_state management for the MathAssistant frontend.

Provides typed accessors for all frontend state, keeping session_state
keys consistent and documented across the application.
"""

import uuid
from typing import TYPE_CHECKING, Optional

import streamlit as st

if TYPE_CHECKING:
    from math_assistant.config import OutputConfig
    from math_assistant.frontend.save_manager import FrontendSaveManager
    from math_assistant.workspace import WorkspaceContext, WorkspaceManager


# ── Key constants ─────────────────────────────────────

class Keys:
    LOGGED_IN = "logged_in"
    TOKEN = "token"
    USER = "user"
    THREAD_ID = "thread_id"
    MESSAGES = "messages"
    LAST_QUESTION_ID = "last_question_id"
    SESSIONS = "sessions"
    BACKEND_URL = "backend_url"
    CONFIG = "config"
    SAVE_MANAGER = "save_manager"
    QUESTION_GROUP_ID = "question_group_id"
    CURRENT_TOPIC = "current_topic"
    # ── Workspace keys ──
    WORKSPACE_CTX = "workspace_ctx"
    WORKSPACE_MGR = "workspace_mgr"
    # ── Summary tab ──
    LATEST_SUMMARY_HTML = "latest_summary_html"


# ── Initialization ────────────────────────────────────

def init_session_state() -> None:
    """Ensure all required keys exist in st.session_state with defaults."""
    defaults = {
        Keys.LOGGED_IN: False,
        Keys.TOKEN: None,
        Keys.USER: None,
        Keys.THREAD_ID: str(uuid.uuid4())[:8],
        Keys.MESSAGES: [],
        Keys.LAST_QUESTION_ID: None,
        Keys.SESSIONS: [],
        Keys.BACKEND_URL: "http://127.0.0.1:8000",
        Keys.CONFIG: None,
    }
    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default


# ── Getters ───────────────────────────────────────────

def is_logged_in() -> bool:
    return st.session_state.get(Keys.LOGGED_IN, False)


def get_token() -> Optional[str]:
    return st.session_state.get(Keys.TOKEN)


def get_user() -> Optional[dict]:
    return st.session_state.get(Keys.USER)


def get_thread_id() -> str:
    return st.session_state[Keys.THREAD_ID]


def get_messages() -> list[dict]:
    return st.session_state[Keys.MESSAGES]


def get_last_question_id() -> Optional[int]:
    return st.session_state.get(Keys.LAST_QUESTION_ID)


def get_backend_url() -> str:
    return st.session_state.get(Keys.BACKEND_URL, "http://127.0.0.1:8000")


def get_save_manager(output_config: "OutputConfig") -> "FrontendSaveManager":
    """Get or create the FrontendSaveManager, cached in session_state."""
    if Keys.SAVE_MANAGER not in st.session_state or st.session_state[Keys.SAVE_MANAGER] is None:
        from math_assistant.frontend.save_manager import FrontendSaveManager
        ws_ctx = get_workspace_ctx()
        st.session_state[Keys.SAVE_MANAGER] = FrontendSaveManager(output_config, ws_ctx)
    return st.session_state[Keys.SAVE_MANAGER]


def get_question_group_id() -> Optional[str]:
    return st.session_state.get(Keys.QUESTION_GROUP_ID)


def set_question_group_id(gid: Optional[str]) -> None:
    st.session_state[Keys.QUESTION_GROUP_ID] = gid


def get_current_topic() -> Optional[str]:
    return st.session_state.get(Keys.CURRENT_TOPIC)


def set_current_topic(topic: Optional[str]) -> None:
    st.session_state[Keys.CURRENT_TOPIC] = topic


# ── Setters ───────────────────────────────────────────

def set_logged_in(token: str, user: dict) -> None:
    st.session_state[Keys.LOGGED_IN] = True
    st.session_state[Keys.TOKEN] = token
    st.session_state[Keys.USER] = user


def set_logged_out() -> None:
    st.session_state[Keys.LOGGED_IN] = False
    st.session_state[Keys.TOKEN] = None
    st.session_state[Keys.USER] = None


def set_thread_id(thread_id: str) -> None:
    st.session_state[Keys.THREAD_ID] = thread_id


def set_messages(messages: list[dict]) -> None:
    st.session_state[Keys.MESSAGES] = messages


def set_last_question_id(qid: int) -> None:
    st.session_state[Keys.LAST_QUESTION_ID] = qid


# ── Message helpers ───────────────────────────────────

def add_user_message(text: str) -> None:
    st.session_state[Keys.MESSAGES].append({"role": "user", "content": text})


def add_assistant_message(text: str) -> None:
    st.session_state[Keys.MESSAGES].append({"role": "assistant", "content": text})


def add_tool_message(tool_name: str, result: str) -> None:
    st.session_state[Keys.MESSAGES].append({
        "role": "tool",
        "tool_name": tool_name,
        "content": result,
    })


def new_conversation() -> None:
    """Reset messages and thread_id for a fresh conversation."""
    st.session_state[Keys.THREAD_ID] = str(uuid.uuid4())[:8]
    st.session_state[Keys.MESSAGES] = []
    st.session_state[Keys.LAST_QUESTION_ID] = None
    # Reset save-related state
    st.session_state[Keys.QUESTION_GROUP_ID] = None
    st.session_state[Keys.CURRENT_TOPIC] = None
    st.session_state[Keys.LATEST_SUMMARY_HTML] = None
    if Keys.SAVE_MANAGER in st.session_state and st.session_state[Keys.SAVE_MANAGER] is not None:
        st.session_state[Keys.SAVE_MANAGER].reset()
    # Create a new workspace for the new conversation
    ws_mgr = get_workspace_mgr()
    if ws_mgr is not None:
        config = st.session_state.get(Keys.CONFIG)
        model = config.main.model if config else ""
        new_ctx = ws_mgr.create_workspace(model=model)
        set_workspace_ctx(new_ctx)
        # Refresh the save manager with the new workspace context
        if Keys.SAVE_MANAGER in st.session_state:
            del st.session_state[Keys.SAVE_MANAGER]


# ── Workspace state accessors ─────────────────────────

def get_workspace_ctx() -> Optional["WorkspaceContext"]:
    """Get the current workspace context from session state."""
    return st.session_state.get(Keys.WORKSPACE_CTX)


def set_workspace_ctx(ctx: Optional["WorkspaceContext"]) -> None:
    """Set the current workspace context in session state."""
    st.session_state[Keys.WORKSPACE_CTX] = ctx


def get_workspace_mgr() -> Optional["WorkspaceManager"]:
    """Get the workspace manager from session state."""
    return st.session_state.get(Keys.WORKSPACE_MGR)


def set_workspace_mgr(mgr: "WorkspaceManager") -> None:
    """Set the workspace manager in session state."""
    st.session_state[Keys.WORKSPACE_MGR] = mgr


# ── Summary HTML tracking ─────────────────────────────

def get_latest_summary_html() -> Optional[str]:
    """Get the path to the latest saved summary HTML file."""
    return st.session_state.get(Keys.LATEST_SUMMARY_HTML)


def set_latest_summary_html(path: Optional[str]) -> None:
    """Set the path to the latest saved summary HTML file."""
    st.session_state[Keys.LATEST_SUMMARY_HTML] = path
