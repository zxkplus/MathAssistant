"""Chat page: the main conversation interface with agent streaming.

Renders chat messages from session_state, handles user input (text + image),
streams agent responses step-by-step, and syncs everything
to the backend API automatically.

Design: tool-call panels use per-tool accent colors; image upload zone
feels like a natural "paste here" target; welcome screen is warm and inviting.
"""

from __future__ import annotations

import re
import uuid
from io import BytesIO
from pathlib import Path
from typing import Optional

import streamlit as st
from PIL import Image

from math_assistant.config import Config
from math_assistant.server.cli_client import MathAssistantBackendClient
from math_assistant.frontend import session_store as store
from math_assistant.frontend.agent_runner import run_agent_stream_cached
from math_assistant.frontend.styles import (
    TOKENS,
    FONT_DISPLAY,
    FONT_BODY,
    get_welcome_html,
    get_tool_panel_css,
)


# ── LaTeX delimiter conversion ──────────────────────────────────────────
# Streamlit's st.markdown() uses KaTeX, which only recognizes $...$ (inline)
# and $$...$$ (display) delimiters.  The LLM often outputs standard LaTeX
# \(...\) and \[...\] which get mangled by markdown's escape processing
# (\[ renders as just [).  We convert them before handing text to st.markdown.

# Match \[...\] – display math.  Use DOTALL so multi-line blocks work.
_DISPLAY_MATH_RE = re.compile(r'\\\[(.*?)\\\]', re.DOTALL)
# Match \(...\) – inline math.
_INLINE_MATH_RE = re.compile(r'\\\((.*?)\\\)', re.DOTALL)


def _fix_latex_delimiters(text: str) -> str:
    """Convert standard LaTeX delimiters to KaTeX-compatible delimiters.

    \[ ... \]  →  $$ ... $$
    \( ... \)  →  $ ... $
    """
    text = _DISPLAY_MATH_RE.sub(r'$$\1$$', text)
    text = _INLINE_MATH_RE.sub(r'$\1$', text)
    return text


def _render_markdown(content: str) -> None:
    """Render markdown content with proper LaTeX rendering.

    Preprocesses LaTeX delimiters then delegates to st.markdown.
    """
    st.markdown(_fix_latex_delimiters(content))


# ── Image handling ──────────────────────────────────────────────────────

_IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.svg', '.gif', '.webp'}
_IMAGE_PATH_RE = re.compile(
    r'(\S+\.(?:png|jpe?g|svg|gif|webp))\b',
    re.IGNORECASE,
)


def _extract_image_paths(text: str, base_dir: str = ".") -> list[Path]:
    """Scan tool output for saved chart/image paths and verify they exist.

    The Python executor prints the file path when a chart is saved
    (e.g. ``images/function_plot.png``).  We detect those lines and
    resolve them against *base_dir* so they survive Streamlit reruns.

    Args:
        text: Raw tool output that may contain image paths.
        base_dir: Working directory to resolve relative paths against.

    Returns:
        List of resolved, existing Path objects for discovered images.
    """
    found: list[Path] = []
    seen: set[str] = set()

    def _try_add(raw: str) -> None:
        candidate = Path(raw.strip().strip('"\''))
        if not candidate.is_absolute():
            candidate = Path(base_dir) / candidate
        key = str(candidate.resolve())
        if key not in seen and candidate.is_file():
            seen.add(key)
            found.append(candidate)

    # 1) Line-based: each line that *ends* with an image extension
    for line in text.split('\n'):
        stripped = line.strip().strip('"\'')
        if not stripped:
            continue
        suffix = Path(stripped).suffix.lower()
        if suffix in _IMAGE_EXTENSIONS:
            _try_add(stripped)

    # 2) Regex fallback: paths embedded in longer lines
    for m in _IMAGE_PATH_RE.finditer(text):
        _try_add(m.group(1))

    return found


def _render_tool_images(tool_content: str, max_images: int = 6) -> None:
    """Scan *tool_content* for image paths and render them with st.image.

    Args:
        tool_content: The raw text output from a tool invocation.
        max_images: Upper bound on how many images to display at once.
    """
    image_paths = _extract_image_paths(tool_content)
    if not image_paths:
        return
    for i, p in enumerate(image_paths[:max_images]):
        st.image(str(p), caption=f"📈 {p.name}", use_container_width=True)
        if i < len(image_paths[:max_images]) - 1:
            st.markdown("")  # spacer


# ── Tool display helpers ────────────────────────────────────────────────

# Map tool names to emoji + display label + accent color
_TOOL_META = {
    "execute_python": {"emoji": "⚙", "label": "Python 执行", "color": TOKENS["ocean"]},
    "web_search":    {"emoji": "🔍", "label": "网络搜索", "color": TOKENS["sage"]},
    "image_to_text": {"emoji": "👁", "label": "图片识别", "color": TOKENS["periwinkle"]},
    "search_papers": {"emoji": "📚", "label": "论文检索", "color": TOKENS["marigold"]},
}
_DEFAULT_TOOL_META = {"emoji": "🔧", "label": "工具调用", "color": TOKENS["ink_soft"]}


def _render_tool_expander(tool_name: str, content: str, step: int) -> None:
    """Render a tool execution as a styled expander card.

    Each tool type gets its own accent color and emoji for visual distinction.
    """
    meta = _TOOL_META.get(tool_name, _DEFAULT_TOOL_META)

    with st.expander(
        f"{meta['emoji']}  {meta['label']}  ·  Step {step}",
        expanded=False,
    ):
        # Tool result display
        tool_display = content[:3000]
        if tool_name == "execute_python":
            st.code(tool_display, language="python")
        else:
            st.text(tool_display)

        # Render any charts generated by the tool
        _render_tool_images(content)


# ── Summary tab ────────────────────────────────────────────────────────

def _render_summary_tab() -> None:
    """Render the session summary HTML in a sandboxed iframe.

    Reads the latest saved summary HTML file and displays it using
    ``st.components.v1.html()``, which isolates the summary's own CSS
    and KaTeX from Streamlit's styles.
    """
    html_path = store.get_latest_summary_html()

    if html_path is None or not Path(html_path).exists():
        st.info(
            "📄 **暂无总结内容**\n\n"
            "开始对话后，总结将自动生成并显示在此处。"
            "每次对话完成后，切换至此分页即可查看最新的对话总结。"
        )
        return

    try:
        html_content = Path(html_path).read_text(encoding="utf-8")

        # Estimate a reasonable iframe height based on content length.
        # This avoids nested scrollbars — the page itself scrolls naturally.
        content_chars = len(html_content)
        estimated_height = max(800, min(30000, 800 + content_chars // 4))

        st.components.v1.html(
            html_content,
            height=estimated_height,
            scrolling=False,
        )
    except Exception:
        st.warning("⚠️ 无法读取总结文件，请尝试发送新消息以重新生成总结。")


# ── Chat page ───────────────────────────────────────────────────────────

def render_chat_page(config: Config) -> None:
    """Render the full chat interface with tabs for conversation and summary.

    Args:
        config: Application config with LLM settings.
    """
    tab_chat, tab_summary = st.tabs(["💬 对话", "📄 总结"])

    with tab_chat:
        # ── Page header ──────────────────────────────────────────────
        st.markdown(
            f"""<h2 style="
                font-family: {FONT_DISPLAY};
                font-weight: 700;
                color: {TOKENS['ink']};
                margin-bottom: 0;
            ">🧮 数学花园</h2>""",
            unsafe_allow_html=True,
        )
        st.caption("AI 数学导师 — 探索、求解、理解数学之美")

        # ── Render existing messages ─────────────────────────────────
        messages = store.get_messages()
        for msg in messages:
            role = msg["role"]
            if role == "user":
                with st.chat_message("user"):
                    st.write(msg["content"])
            elif role == "assistant":
                with st.chat_message("assistant"):
                    _render_markdown(msg["content"])
            elif role == "tool":
                tool_name = msg.get("tool_name", "tool")
                tool_content = msg.get("content", "")
                with st.expander(
                    f"🛠 {tool_name}",
                    expanded=False,
                ):
                    if tool_name == "execute_python":
                        st.code(tool_content[:2000], language="python")
                    else:
                        st.text(tool_content[:2000])
                    _render_tool_images(tool_content)

        # ── Welcome message ──────────────────────────────────────────
        if not messages:
            st.markdown(get_welcome_html(), unsafe_allow_html=True)

        # ── Image upload area ────────────────────────────────────────
        _render_image_upload_area(config)

        # ── Chat input ───────────────────────────────────────────────
        if prompt := st.chat_input("输入你的数学问题…"):
            _handle_user_input(prompt, config)

    with tab_summary:
        _render_summary_tab()


# ── Image upload & OCR helpers ────────────────────────────────────────────

_IMG_KEY_UPLOADED = "_mathassist_uploaded_image"
_IMG_KEY_EXTRACTED = "_mathassist_extracted_text"
_IMG_KEY_SAVED_PATH = "_mathassist_saved_image_path"


def _render_image_upload_area(config: Config) -> None:
    """Render a paste-friendly image upload area above the chat input.

    Three ways to input an image:
    1. **Ctrl+V paste** — click the upload area, then press Ctrl+V
    2. **Drag-and-drop** — drag an image file onto the upload area
    3. **Click to browse** — click "Browse files" to select from disk
    """
    with st.container(border=True):
        st.markdown(
            f"""<p style="
                font-family: {FONT_BODY};
                font-size: 0.85rem;
                color: {TOKENS['ink_soft']};
                margin: 0 0 0.25rem 0;
                text-align: center;
            ">📸 <strong>截图粘贴区</strong> — 点击下方区域后 Ctrl+V 粘贴，或拖拽图片至此</p>""",
            unsafe_allow_html=True,
        )

        uploaded_file = st.file_uploader(
            "粘贴截图 / 拖拽图片 / 点击上传",
            type=["png", "jpg", "jpeg", "webp", "gif", "bmp"],
            key="_mathassist_image_uploader",
            help="🎯 点击此区域，然后 Ctrl+V 粘贴截图！也支持拖拽和点击选择文件。",
            label_visibility="collapsed",
        )

    # ── Process uploaded/pasted image ──────────────────────────────
    if uploaded_file is not None:
        file_bytes = uploaded_file.getvalue()

        # Hash-based dedup: only process when a genuinely new image arrives
        new_hash = hash(file_bytes)
        last_hash = st.session_state.get(f"{_IMG_KEY_UPLOADED}_hash")

        if last_hash != new_hash:
            st.session_state[f"{_IMG_KEY_UPLOADED}_hash"] = new_hash
            st.session_state[_IMG_KEY_UPLOADED] = file_bytes

            # Save image to workspace images dir
            ws_ctx = store.get_workspace_ctx()
            save_dir = ws_ctx.images_dir if ws_ctx else Path(config.output.image_dir)
            save_dir.mkdir(parents=True, exist_ok=True)
            stem = uuid.uuid4().hex[:8]
            image = Image.open(BytesIO(file_bytes))
            saved_path = save_dir / f"upload_{stem}.png"
            image.save(str(saved_path))
            st.session_state[_IMG_KEY_SAVED_PATH] = str(saved_path)

            # OCR extraction
            with st.spinner("🔍 正在识别图片中的题目…"):
                extracted = _extract_text_from_image(saved_path, config)
            st.session_state[_IMG_KEY_EXTRACTED] = extracted

            st.rerun()

    # ── Show uploaded image + editable OCR result ──────────────────
    if st.session_state.get(_IMG_KEY_SAVED_PATH):
        extracted = st.session_state.get(_IMG_KEY_EXTRACTED, "")
        saved_path = st.session_state.get(_IMG_KEY_SAVED_PATH, "")

        col_img, col_text = st.columns([1, 2])
        with col_img:
            if Path(saved_path).exists():
                st.image(saved_path, caption="上传的图片", use_container_width=True)
        with col_text:
            st.markdown(
                f"""<p style="
                    font-family: {FONT_BODY};
                    font-size: 0.8rem;
                    color: {TOKENS['ink_muted']};
                    margin: 0 0 0.25rem 0;
                ">📝 识别结果（可编辑修正）</p>""",
                unsafe_allow_html=True,
            )
            corrected = st.text_area(
                "识别文本",
                value=extracted,
                height=200,
                key="_mathassist_ocr_result",
                label_visibility="collapsed",
            )
            if corrected != extracted:
                st.session_state[_IMG_KEY_EXTRACTED] = corrected

            if st.button("❌ 清除图片", key="_mathassist_clear_image"):
                _clear_uploaded_image()
                st.rerun()


def _extract_text_from_image(image_path: str, config: Config) -> str:
    """Use the vision provider to extract math text from an image."""
    try:
        from math_assistant.vision_providers import get_vision_provider

        provider = get_vision_provider(
            "openai",
            model=config.vision.model,
            api_key=config.vision.api_key,
            base_url=config.vision.base_url,
        )
        result = provider.image_to_text(str(image_path))
        if result.startswith("Error:"):
            return result
        return result
    except ValueError as e:
        return f"Error: Vision provider not configured — {e}"
    except Exception as e:
        return f"Error: OCR extraction failed — {e}"


def _clear_uploaded_image() -> None:
    """Clear all uploaded image tracking state."""
    st.session_state.pop(f"{_IMG_KEY_UPLOADED}_hash", None)
    st.session_state.pop(_IMG_KEY_UPLOADED, None)
    st.session_state.pop(_IMG_KEY_EXTRACTED, None)
    st.session_state.pop(_IMG_KEY_SAVED_PATH, None)


def _build_combined_message(user_text: str) -> str:
    """Combine extracted image text with user's supplementary notes."""
    extracted = st.session_state.get(_IMG_KEY_EXTRACTED, "")
    saved_path = st.session_state.get(_IMG_KEY_SAVED_PATH, "")

    parts: list[str] = []

    if extracted and not extracted.startswith("Error:"):
        parts.append(
            f"【以下内容已通过 OCR 自动识别，请直接使用，无需再次调用 image_to_text 工具】\n"
            f"{extracted}"
        )
    elif extracted and extracted.startswith("Error:"):
        if saved_path:
            parts.append(
                f"【图片 OCR 失败】错误信息: {extracted}\n\n"
                f"请使用 image_to_text 工具读取以下路径的图片: {saved_path}"
            )
        else:
            parts.append(f"【图片 OCR 失败】{extracted}")

    if user_text.strip():
        if parts:
            parts.append(f"\n【学生的补充说明】\n{user_text}")
        else:
            parts.append(user_text)

    return "\n\n".join(parts) if parts else user_text


# ── User input handling ───────────────────────────────────────────────────

def _handle_user_input(prompt: str, config: Config) -> None:
    """Process a user message: combine with image OCR if present, run agent, sync.

    Args:
        prompt: The user's input text.
        config: Application config.
    """
    # ── Build the combined message (image OCR + user text) ──
    combined_prompt = _build_combined_message(prompt)
    has_image = st.session_state.get(_IMG_KEY_SAVED_PATH) is not None

    # Add user message to state
    store.add_user_message(combined_prompt)

    # Display user message immediately
    with st.chat_message("user"):
        st.write(prompt)
        if has_image:
            saved_path = st.session_state.get(_IMG_KEY_SAVED_PATH, "")
            if Path(saved_path).exists():
                st.image(saved_path, caption="上传的图片", width=300)
            extracted = st.session_state.get(_IMG_KEY_EXTRACTED, "")
            if extracted and not extracted.startswith("Error:"):
                with st.expander("📝 识别文本", expanded=False):
                    st.text(extracted[:500])

    # Clear uploaded image state after use
    _clear_uploaded_image()

    # Submit question to backend (non-blocking best-effort)
    question_id = _submit_to_backend(combined_prompt)

    # ── Auto-save: init save manager & classify question ──
    save_mgr = store.get_save_manager(config.output)
    is_new_group = save_mgr.classify_and_start_group(combined_prompt)
    if is_new_group:
        store.set_question_group_id(save_mgr.recorder.get_current_group().group_id)  # type: ignore[union-attr]
        store.set_current_topic(combined_prompt)
    save_mgr.recorder.start_turn(combined_prompt)

    # Run agent with streaming
    thread_id = store.get_thread_id()

    with st.chat_message("assistant"):
        text_placeholder = st.empty()

        full_response_parts: list[str] = []
        step_count = 0

        try:
            ws_ctx = store.get_workspace_ctx()
            image_dir = str(ws_ctx.images_dir) if ws_ctx else config.output.image_dir
            for event in run_agent_stream_cached(
                combined_prompt, thread_id, config, image_dir=image_dir,
            ):
                node = event["node"]
                msg_type = event["type"]
                content = event.get("content", "")

                step_count += 1

                if msg_type == "AIMessage" and node == "model":
                    # Step indicator with subtle styling
                    st.markdown(
                        f"""<p style="
                            font-family: {FONT_BODY};
                            font-size: 0.78rem;
                            color: {TOKENS['ink_muted']};
                            margin: 0.35rem 0;
                        ">💭 Step {step_count} · 推理中…</p>""",
                        unsafe_allow_html=True,
                    )
                    if content.strip():
                        full_response_parts.append(content)
                        combined = "\n\n".join(full_response_parts)
                        text_placeholder.markdown(_fix_latex_delimiters(combined))

                    # Record assistant text for save
                    save_mgr.recorder.add_assistant_text(content)
                    if event.get("tool_calls"):
                        for tc in event["tool_calls"]:
                            save_mgr.recorder.record_tool_call(
                                name=tc.get("name", "unknown"),
                                args=tc.get("args", {}),
                            )

                elif msg_type == "ToolMessage" and node == "tools":
                    tool_name = event.get("tool_name", "unknown")
                    _render_tool_expander(tool_name, content, step_count)

                    # Record tool message for history
                    store.add_tool_message(tool_name, content[:1000])
                    save_mgr.recorder.record_tool_result(
                        name=tool_name,
                        output=content,
                    )

            # Final render
            final_text = "\n\n".join(full_response_parts)
            if final_text.strip():
                text_placeholder.markdown(_fix_latex_delimiters(final_text))
                store.add_assistant_message(final_text)
            else:
                text_placeholder.markdown(
                    f"""<p style="
                        font-family: {FONT_BODY};
                        color: {TOKENS['ink_muted']};
                        font-style: italic;
                    ">(模型未产生输出)</p>""",
                    unsafe_allow_html=True,
                )

        except Exception as e:
            text_placeholder.error(f"运行出错: {e}")

        finally:
            # Auto-save: finalize turn and save question group
            try:
                turn = save_mgr.recorder.end_turn()
                if save_mgr.recorder.get_current_group() is not None:
                    save_mgr.recorder.add_turn_to_current_group(turn)
                    _md_path, html_path = save_mgr.save_current_group()
                    if html_path is not None:
                        store.set_latest_summary_html(str(html_path))
            except Exception:
                pass

    # Feedback buttons
    if full_response_parts and question_id:
        _render_feedback_buttons(question_id, store.get_backend_url())

    if question_id:
        store.set_last_question_id(question_id)


def _submit_to_backend(question_text: str) -> Optional[int]:
    """Submit question to the backend API for persistence and auto-tagging."""
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
    """Render thumbs-up/down buttons for answer feedback."""
    token = store.get_token()
    if not token:
        return

    col1, col2, col3, col4 = st.columns([1, 1, 1, 6])
    with col1:
        if st.button("👍", key=f"correct_{question_id}", help="回答正确"):
            _record_feedback(question_id, True, backend_url, token)
            st.success("已标记为正确！")
    with col2:
        if st.button("👎", key=f"wrong_{question_id}", help="回答有误"):
            _record_feedback(question_id, False, backend_url, token)
            st.warning("已加入错题本")


def _record_feedback(
    question_id: int,
    is_correct: bool,
    backend_url: str,
    token: str,
) -> None:
    """Record answer correctness feedback to the backend."""
    try:
        client = MathAssistantBackendClient(base_url=backend_url, token=token)
        client.record_answer(
            question_id=question_id,
            is_correct=is_correct,
            mistake_type=None if is_correct else "unknown",
        )
    except Exception:
        pass
