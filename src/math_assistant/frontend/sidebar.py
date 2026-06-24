"""Sidebar: session management, learning stats, and current-topic tags.

All data is fetched from the backend API via MathAssistantBackendClient.
"""

import streamlit as st

from math_assistant.server.cli_client import MathAssistantBackendClient
from math_assistant.frontend import session_store as store


def render_sidebar() -> None:
    """Render the full sidebar with all sections.

    Returns nothing — all UI is rendered via st.sidebar.* calls.
    """
    user = store.get_user()
    token = store.get_token()
    backend_url = store.get_backend_url()

    with st.sidebar:
        # ── Header ──────────────────────────────
        st.markdown("## 🧮 MathAssistant")
        if user:
            st.caption(f"👤 {user.get('display_name') or user.get('username', '')}")

        st.divider()

        # ── New Conversation ────────────────────
        if st.button("📝 新建对话", use_container_width=True):
            store.new_conversation()
            st.rerun()

        st.divider()

        # ── History Sessions ────────────────────
        st.markdown("### 📚 历史对话")
        if token:
            try:
                client = MathAssistantBackendClient(base_url=backend_url, token=token)
                # Fetch recent questions grouped by date
                questions = client.list_questions(per_page=50)
                _render_history(questions.get("items", []), client)
            except Exception:
                st.caption("无法加载历史对话")

        st.divider()

        # ── Learning Stats ──────────────────────
        st.markdown("### 📊 学习统计")
        if token:
            try:
                client = MathAssistantBackendClient(base_url=backend_url, token=token)
                summary = client.get_summary()
                st.metric("总体正确率", f"{summary.get('overall_accuracy', 0):.0f}%")
                st.metric("知识点", summary.get("topics_explored", 0))
                st.metric("连续天数", f"{summary.get('streak_days', 0)} 🔥")
            except Exception:
                st.caption("暂无统计数据")

        st.divider()

        # ── Current Session Tags ────────────────
        st.markdown("### 🏷 当前标签")
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
                        st.caption(f"{src} {name} ({conf:.0%})")
                else:
                    st.caption("等待自动标注...")
            except Exception:
                pass

        st.divider()

        # ── Logout ──────────────────────────────
        if st.button("🚪 退出登录", use_container_width=True):
            store.set_logged_out()
            st.rerun()


def _render_history(questions: list[dict], client: MathAssistantBackendClient) -> None:
    """Render a grouped history of past questions."""
    seen_dates: set[str] = set()
    for q in questions[:20]:
        date_str = q.get("created_at", "")[:10]
        content = q.get("content", "")
        preview = content[:50] + "..." if len(content) > 50 else content

        if date_str not in seen_dates:
            seen_dates.add(date_str)
            st.caption(f"📅 {date_str}")

        # Make each question clickable to load its full context
        if st.button(f"📌 {preview}", key=f"hist_{q['id']}", use_container_width=True):
            _load_history_question(q["id"], client)


def _load_history_question(question_id: int, client: MathAssistantBackendClient) -> None:
    """Load a historical question into the current chat view."""
    try:
        q_data = client.get_question(question_id)
        # Add the question and any answer records as messages
        msgs = []
        msgs.append({"role": "user", "content": q_data["content"]})
        for record in q_data.get("answer_records", []):
            # We can't recover the full assistant response from answer records,
            # but we can show that this question was previously answered
            pass
        # For now, just load the question as a user message
        store.add_user_message(q_data["content"])
        store.set_last_question_id(question_id)
        st.rerun()
    except Exception as e:
        st.error(f"Failed to load question: {e}")
