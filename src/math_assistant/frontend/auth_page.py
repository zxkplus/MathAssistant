"""Authentication page: Login and Register tabs.

Uses the backend API via MathAssistantBackendClient for auth operations.
"""

import streamlit as st

from math_assistant.server.cli_client import MathAssistantBackendClient
from math_assistant.frontend import session_store as store


def render_auth_page() -> None:
    """Render the login/register page.

    On successful authentication, updates session_state and triggers
    a rerun so the main app switches to the chat page.
    """
    # Center the auth card
    _, col, _ = st.columns([1, 2, 1])

    with col:
        st.markdown("""
        <h1 style='text-align: center;'>🧮 MathAssistant</h1>
        <p style='text-align: center; color: #888; margin-bottom: 2rem;'>
            AI-Powered Mathematics Teacher
        </p>
        """, unsafe_allow_html=True)

        tab_login, tab_register = st.tabs(["🔑 Login", "📝 Register"])

        # ── Login Tab ─────────────────────────────
        with tab_login:
            with st.form("login_form", clear_on_submit=False):
                username = st.text_input("Username", key="login_username")
                password = st.text_input("Password", type="password", key="login_password")
                submitted = st.form_submit_button("Login", type="primary", use_container_width=True)

                if submitted:
                    if not username or not password:
                        st.error("Please enter both username and password.")
                    else:
                        _do_login(username, password)

        # ── Register Tab ──────────────────────────
        with tab_register:
            with st.form("register_form", clear_on_submit=False):
                reg_username = st.text_input("Username", key="reg_username",
                    help="3-64 characters, letters, numbers, underscores")
                reg_email = st.text_input("Email", key="reg_email")
                reg_display = st.text_input("Display Name (optional)", key="reg_display")
                reg_password = st.text_input("Password", type="password", key="reg_password",
                    help="Minimum 8 characters")
                reg_submitted = st.form_submit_button("Register", type="primary", use_container_width=True)

                if reg_submitted:
                    if not reg_username or not reg_email or not reg_password:
                        st.error("Please fill in all required fields.")
                    elif len(reg_password) < 8:
                        st.error("Password must be at least 8 characters.")
                    else:
                        _do_register(reg_username, reg_email, reg_password, reg_display or None)


def _do_login(username: str, password: str) -> None:
    """Attempt login via backend API."""
    backend_url = store.get_backend_url()
    client = MathAssistantBackendClient(base_url=backend_url)

    try:
        result = client.login(username, password)
        store.set_logged_in(token=result["access_token"], user=result["user"])
        st.rerun()
    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg:
            st.error("Invalid username or password.")
        else:
            st.error(f"Login failed: {error_msg}")


def _do_register(username: str, email: str, password: str, display_name: str | None) -> None:
    """Attempt registration via backend API."""
    backend_url = store.get_backend_url()
    client = MathAssistantBackendClient(base_url=backend_url)

    try:
        client.register(username, email, password, display_name)
        st.success(f"Account created! Please switch to the Login tab to sign in as **{username}**.")
    except Exception as e:
        error_msg = str(e)
        if "409" in error_msg or "already" in error_msg.lower():
            st.error("Username or email is already registered.")
        else:
            st.error(f"Registration failed: {error_msg}")
