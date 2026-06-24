"""Streamlit session_state management for the MathAssistant frontend.

Provides typed accessors for all frontend state, keeping session_state
keys consistent and documented across the application.
"""

import uuid
from typing import Optional

import streamlit as st


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
