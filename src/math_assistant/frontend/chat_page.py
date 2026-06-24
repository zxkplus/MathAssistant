"""Chat page: the main conversation interface with agent streaming.

Renders chat messages from session_state, handles user input,
streams agent responses step-by-step, and syncs everything
to the backend API automatically.
"""

import time
from typing import Optional

import streamlit as st

from math_assistant.config import Config
from math_assistant.server.cli_client import MathAssistantBackendClient
from math_assistant.frontend import session_store as store
from math_assistant.frontend.agent_runner import run_agent_stream_cached


def render_chat_page(config: Config) -> None:
    """Render the full chat interface.

    Args:
        config: Application config with LLM settings.
    """
    st.markdown("## 🧮 MathAssistant")
    st.caption("AI-Powered Mathematics Teacher — ask me anything about math!")

    # Render existing messages
    messages = store.get_messages()
    for msg in messages:
        role = msg["role"]
        if role == "user":
            with st.chat_message("user"):
                st.write(msg["content"])
        elif role == "assistant":
            with st.chat_message("assistant"):
                st.markdown(msg["content"])
        elif role == "tool":
            with st.expander(f"🛠 {msg.get('tool_name', 'tool')}", expanded=False):
                st.code(msg.get("content", "")[:2000], language=None)

    # Welcome message if no messages yet
    if not messages:
        with st.chat_message("assistant"):
            st.markdown("""
            👋 你好！我是 MathAssistant，你的 AI 数学导师。

            我可以帮你：
            - 📐 求解方程、求导、积分、矩阵运算
            - 📊 绘制函数图像
            - 📖 解释数学概念和定理
            - 🔍 搜索数学资料

            **试试问我一个问题吧！**
            """)

    # Chat input
    if prompt := st.chat_input("输入你的数学问题..."):
        _handle_user_input(prompt, config)


def _handle_user_input(prompt: str, config: Config) -> None:
    """Process a user message: add to state, run agent, sync to backend.

    Args:
        prompt: The user's input text.
        config: Application config.
    """
    # Add user message to state
    store.add_user_message(prompt)

    # Display user message immediately
    with st.chat_message("user"):
        st.write(prompt)

    # Submit question to backend (non-blocking best-effort)
    question_id = _submit_to_backend(prompt)

    # Run agent with streaming
    thread_id = store.get_thread_id()

    with st.chat_message("assistant"):
        # Placeholder for real-time streaming
        text_placeholder = st.empty()
        tool_expanders: dict[str, st.expander] = {}

        full_response_parts: list[str] = []
        step_count = 0

        try:
            for event in run_agent_stream_cached(prompt, thread_id, config):
                node = event["node"]
                msg_type = event["type"]
                content = event.get("content", "")

                step_count += 1

                if msg_type == "AIMessage" and node == "model":
                    # Show step indicator
                    st.caption(f"💭 Step {step_count}: reasoning...")
                    if content.strip():
                        full_response_parts.append(content)
                        # Render accumulated text so far
                        text_placeholder.markdown("\n\n".join(full_response_parts))

                elif msg_type == "ToolMessage" and node == "tools":
                    tool_name = event.get("tool_name", "unknown")
                    # Show tool call in expander
                    tool_key = f"tool_{step_count}_{tool_name}"
                    with st.expander(f"🛠 {tool_name} (Step {step_count})", expanded=False):
                        tool_display = content[:3000]
                        if tool_name == "execute_python":
                            st.code(tool_display, language="python")
                        else:
                            st.text(tool_display)

                    # Record tool message for history
                    store.add_tool_message(tool_name, content[:1000])

            # Final render: all text
            final_text = "\n\n".join(full_response_parts)
            if final_text.strip():
                text_placeholder.markdown(final_text)
                store.add_assistant_message(final_text)
            else:
                text_placeholder.markdown("*(No output generated)*")

        except Exception as e:
            text_placeholder.error(f"Error: {e}")

    # Record answer feedback buttons (only if we got a response)
    if full_response_parts and question_id:
        _render_feedback_buttons(question_id, store.get_backend_url())

    # Refresh sidebar data
    if question_id:
        store.set_last_question_id(question_id)


def _submit_to_backend(question_text: str) -> Optional[int]:
    """Submit question to the backend API for persistence and auto-tagging.

    Args:
        question_text: The user's question.

    Returns:
        question_id if successful, None otherwise.
    """
    token = store.get_token()
    if not token:
        return None

    backend_url = store.get_backend_url()
    try:
        client = MathAssistantBackendClient(base_url=backend_url, token=token)
        result = client.submit_question(question_text, source="web")
        return result.get("id")
    except Exception:
        return None


def _render_feedback_buttons(question_id: int, backend_url: str) -> None:
    """Render thumbs-up/down buttons for answer feedback.

    Args:
        question_id: The backend question ID to record feedback against.
        backend_url: Backend server URL.
    """
    token = store.get_token()
    if not token:
        return

    col1, col2, col3, col4 = st.columns([1, 1, 1, 6])
    with col1:
        if st.button("👍", key=f"correct_{question_id}", help="Mark as correct"):
            _record_feedback(question_id, True, backend_url, token)
            st.success("Marked as correct!")
    with col2:
        if st.button("👎", key=f"wrong_{question_id}", help="Mark as incorrect"):
            _record_feedback(question_id, False, backend_url, token)
            st.warning("Added to mistake notebook")


def _record_feedback(
    question_id: int,
    is_correct: bool,
    backend_url: str,
    token: str,
) -> None:
    """Record answer correctness feedback to the backend.

    Args:
        question_id: The question ID.
        is_correct: Whether the answer was correct.
        backend_url: Backend server URL.
        token: JWT auth token.
    """
    try:
        client = MathAssistantBackendClient(base_url=backend_url, token=token)
        client.record_answer(
            question_id=question_id,
            is_correct=is_correct,
            mistake_type=None if is_correct else "unknown",
        )
    except Exception:
        pass  # Silently fail — feedback is best-effort
