"""Authentication page: Login and Register tabs.

Uses the backend API via MathAssistantBackendClient for auth operations.

Design: centered card layout with the "数学花园" brand header, clean form styling,
and warm, inviting error/success messages.
"""

from __future__ import annotations

import streamlit as st

from math_assistant.server.cli_client import MathAssistantBackendClient
from math_assistant.frontend import session_store as store
from math_assistant.frontend.styles import get_auth_header_html


def render_auth_page() -> None:
    """Render the login/register page.

    On successful authentication, updates session_state and triggers
    a rerun so the main app switches to the chat page.
    """
    # Center the auth card — use a generous center column
    _, col, _ = st.columns([0.8, 2, 0.8])

    with col:
        # Space above the card for visual breathing room
        st.markdown("<br>", unsafe_allow_html=True)

        # Brand header
        st.markdown(get_auth_header_html(), unsafe_allow_html=True)

        # Tabs for login / register
        tab_login, tab_register = st.tabs(["🔑 登录", "📝 注册"])

        # ── Login Tab ─────────────────────────────────────────
        with tab_login:
            with st.form("login_form", clear_on_submit=False):
                username = st.text_input(
                    "用户名",
                    key="login_username",
                    placeholder="请输入用户名",
                )
                password = st.text_input(
                    "密码",
                    type="password",
                    key="login_password",
                    placeholder="请输入密码",
                )
                submitted = st.form_submit_button(
                    "登 录",
                    type="primary",
                    use_container_width=True,
                )

                if submitted:
                    if not username or not password:
                        st.error("请输入用户名和密码。")
                    else:
                        _do_login(username, password)

        # ── Register Tab ──────────────────────────────────────
        with tab_register:
            with st.form("register_form", clear_on_submit=False):
                reg_username = st.text_input(
                    "用户名",
                    key="reg_username",
                    placeholder="3-64 个字符，字母、数字、下划线",
                    help="3-64 characters, letters, numbers, underscores",
                )
                reg_email = st.text_input(
                    "邮箱",
                    key="reg_email",
                    placeholder="your@email.com",
                )
                reg_display = st.text_input(
                    "显示名称（选填）",
                    key="reg_display",
                    placeholder="你的昵称",
                )
                reg_password = st.text_input(
                    "密码",
                    type="password",
                    key="reg_password",
                    placeholder="至少 8 个字符",
                    help="Minimum 8 characters",
                )
                reg_submitted = st.form_submit_button(
                    "注 册",
                    type="primary",
                    use_container_width=True,
                )

                if reg_submitted:
                    if not reg_username or not reg_email or not reg_password:
                        st.error("请填写所有必填字段。")
                    elif len(reg_password) < 8:
                        st.error("密码至少需要 8 个字符。")
                    else:
                        _do_register(
                            reg_username, reg_email, reg_password, reg_display or None,
                        )


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
            st.error("用户名或密码错误，请重试。")
        else:
            st.error(f"登录失败: {error_msg}")


def _do_register(
    username: str, email: str, password: str, display_name: str | None,
) -> None:
    """Attempt registration via backend API."""
    backend_url = store.get_backend_url()
    client = MathAssistantBackendClient(base_url=backend_url)

    try:
        client.register(username, email, password, display_name)
        st.success(f"账号创建成功！请切换到「登录」标签页以 **{username}** 身份登录。")
    except Exception as e:
        error_msg = str(e)
        if "409" in error_msg or "already" in error_msg.lower():
            st.error("用户名或邮箱已被注册。")
        else:
            st.error(f"注册失败: {error_msg}")
