"""Sidebar: session management, learning stats, and current-topic tags.

All data is fetched from the backend API via MathAssistantBackendClient.

Design: the sidebar is the "notebook margin" — a warm, organized space for
navigation, stats, and metadata, visually distinct from the main chat area.
"""

from __future__ import annotations

import streamlit as st

from math_assistant.server.cli_client import MathAssistantBackendClient
from math_assistant.frontend import session_store as store
from math_assistant.frontend.styles import TOKENS, FONT_DISPLAY, FONT_BODY


def render_sidebar() -> None:
    """Render the full sidebar with all sections.

    Returns nothing — all UI is rendered via st.sidebar.* calls.
    """
    user = store.get_user()
    token = store.get_token()
    backend_url = store.get_backend_url()

    with st.sidebar:
        # ── Header ──────────────────────────────────────────────
        st.markdown(
            f"""<div style="
                font-family: {FONT_DISPLAY};
                font-size: 1.3rem;
                font-weight: 700;
                color: {TOKENS['ink']};
                margin-bottom: 0.15rem;
            ">🧮 数学花园</div>""",
            unsafe_allow_html=True,
        )
        if user:
            display = user.get("display_name") or user.get("username", "")
            st.markdown(
                f"""<p style="
                    font-family: {FONT_BODY};
                    font-size: 0.82rem;
                    color: {TOKENS['ink_soft']};
                    margin: 0 0 0.5rem 0;
                ">👤 {display}</p>""",
                unsafe_allow_html=True,
            )

        st.divider()

        # ── New Conversation ────────────────────────────────────
        if st.button("📝 新建对话", use_container_width=True, type="primary"):
            store.new_conversation()
            st.rerun()

        st.divider()

        # ── History ─────────────────────────────────────────────
        st.markdown(
            f"""<p style="
                font-family: {FONT_DISPLAY};
                font-size: 0.9rem;
                font-weight: 600;
                color: {TOKENS['ink']};
                margin-bottom: 0.5rem;
            ">📚 历史对话</p>""",
            unsafe_allow_html=True,
        )
        if token:
            try:
                client = MathAssistantBackendClient(base_url=backend_url, token=token)
                questions = client.list_questions(per_page=50)
                _render_history(questions.get("items", []), client)
            except Exception:
                st.caption("无法加载历史对话")
        else:
            st.caption("登录后可查看历史对话")

        st.divider()

        # ── Learning Stats ──────────────────────────────────────
        st.markdown(
            f"""<p style="
                font-family: {FONT_DISPLAY};
                font-size: 0.9rem;
                font-weight: 600;
                color: {TOKENS['ink']};
                margin-bottom: 0.5rem;
            ">📊 学习统计</p>""",
            unsafe_allow_html=True,
        )
        if token:
            try:
                client = MathAssistantBackendClient(base_url=backend_url, token=token)
                summary = client.get_summary()
                col_a, col_b = st.columns(2)
                with col_a:
                    st.metric(
                        "正确率",
                        f"{summary.get('overall_accuracy', 0):.0f}%",
                    )
                with col_b:
                    st.metric(
                        "连续天数",
                        f"{summary.get('streak_days', 0)} 🔥",
                    )
                col_c, col_d = st.columns(2)
                with col_c:
                    st.metric(
                        "知识点",
                        summary.get("topics_explored", 0),
                    )
                with col_d:
                    st.metric(
                        "问题数",
                        summary.get("total_questions", 0),
                    )
            except Exception:
                st.caption("暂无统计数据")
        else:
            st.caption("登录后可查看学习统计")

        st.divider()

        # ── Current Tags ────────────────────────────────────────
        st.markdown(
            f"""<p style="
                font-family: {FONT_DISPLAY};
                font-size: 0.9rem;
                font-weight: 600;
                color: {TOKENS['ink']};
                margin-bottom: 0.5rem;
            ">🏷 当前标签</p>""",
            unsafe_allow_html=True,
        )
        qid = store.get_last_question_id()
        if qid and token:
            try:
                client = MathAssistantBackendClient(base_url=backend_url, token=token)
                q_data = client.get_question(qid)
                tags = q_data.get("tags", [])
                if tags:
                    for tag in tags:
                        name = tag.get("knowledge_point_name", "Unknown")
                        conf = tag.get("confidence", 0)
                        src = "✏️" if tag.get("source") == "manual" else "🤖"
                        st.markdown(
                            f"""<p style="
                                font-family: {FONT_BODY};
                                font-size: 0.8rem;
                                color: {TOKENS['ink_soft']};
                                margin: 0.15rem 0;
                            ">{src} {name} <span style="
                                color: {TOKENS['ink_muted']};
                                font-size: 0.75rem;
                            ">({conf:.0%})</span></p>""",
                            unsafe_allow_html=True,
                        )
                else:
                    st.caption("等待自动标注…")
            except Exception:
                pass
        else:
            st.caption("开始对话后将自动标注知识点")

        st.divider()

        # ── Logout ──────────────────────────────────────────────
        if st.button("🚪 退出登录", use_container_width=True):
            store.set_logged_out()
            st.rerun()


def _render_history(questions: list[dict], client: MathAssistantBackendClient) -> None:
    """Render a grouped history of past questions.

    Questions are grouped by date and shown as clickable preview buttons.
    """
    if not questions:
        st.caption("暂无历史对话")
        return

    seen_dates: set[str] = set()
    for q in questions[:20]:
        date_str = q.get("created_at", "")[:10]
        content = q.get("content", "")
        preview = content[:45] + "…" if len(content) > 45 else content

        if date_str not in seen_dates:
            seen_dates.add(date_str)
            st.markdown(
                f"""<p style="
                    font-family: {FONT_BODY};
                    font-size: 0.72rem;
                    font-weight: 600;
                    color: {TOKENS['ink_muted']};
                    margin: 0.5rem 0 0.15rem 0;
                    text-transform: uppercase;
                    letter-spacing: 0.05em;
                ">📅 {date_str}</p>""",
                unsafe_allow_html=True,
            )

        if st.button(
            f"📌 {preview}",
            key=f"hist_{q['id']}",
            use_container_width=True,
        ):
            _load_history_question(q["id"], client)


def _load_history_question(question_id: int, client: MathAssistantBackendClient) -> None:
    """Load a historical question into the current chat view."""
    try:
        q_data = client.get_question(question_id)
        store.add_user_message(q_data["content"])
        store.set_last_question_id(question_id)
        st.rerun()
    except Exception as e:
        st.error(f"加载失败: {e}")
