"""Chat page: the main conversation interface with agent streaming.

Renders chat messages from session_state, handles user input (text + image),
streams agent responses step-by-step, and syncs everything
to the backend API automatically.
"""

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


# Image extensions that the Python executor may generate
_IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.svg', '.gif', '.webp'}
# Fallback regex for paths embedded in longer lines (e.g. "Saved to images/plot.png")
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
    for p in image_paths[:max_images]:
        st.image(str(p), caption=p.name, use_container_width=True)


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
                _render_markdown(msg["content"])
        elif role == "tool":
            with st.expander(f"🛠 {msg.get('tool_name', 'tool')}", expanded=False):
                tool_content = msg.get("content", "")
                tool_name = msg.get("tool_name", "")
                if tool_name == "execute_python":
                    st.code(tool_content[:2000], language="python")
                else:
                    st.text(tool_content[:2000])
                # Show generated charts
                _render_tool_images(tool_content)

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
            - 📸 识别图片中的数学题目（支持粘贴截图）

            **试试问我一个问题，或者直接粘贴一张题目图片吧！**
            """)

    # ── Image upload area ──
    _render_image_upload_area(config)

    # Chat input
    if prompt := st.chat_input("输入你的数学问题（可补充说明上传的图片）..."):
        _handle_user_input(prompt, config)


# ── Image upload & OCR helpers ────────────────────────────────────────────

# Session-state keys for image upload flow
_IMG_KEY_UPLOADED = "_mathassist_uploaded_image"
_IMG_KEY_EXTRACTED = "_mathassist_extracted_text"
_IMG_KEY_SAVED_PATH = "_mathassist_saved_image_path"


def _render_image_upload_area(config: Config) -> None:
    """Render a paste-friendly image upload area above the chat input.

    Provides three ways to input an image:
    1. **Ctrl+V paste** — click the upload area, then press Ctrl+V to paste a screenshot
    2. **Drag-and-drop** — drag an image file onto the upload area
    3. **Click to browse** — click "Browse files" to select from disk

    Uploaded images are immediately OCR-extracted via the vision provider.
    The extracted text is shown in an editable area for user verification.
    """

    # ── Paste-friendly upload area ─────────────────────────────────
    # st.file_uploader is an HTML <input type="file"> which natively
    # supports paste (Ctrl+V) when focused, plus drag-and-drop.
    # We wrap it in a styled container to make the paste zone obvious.
    with st.container(border=True):
        st.caption("📸 **截图粘贴区** — 点击下方区域，然后 Ctrl+V 粘贴截图")

        uploaded_file = st.file_uploader(
            "粘贴截图 / 拖拽图片 / 点击上传",
            type=["png", "jpg", "jpeg", "webp", "gif", "bmp"],
            key="_mathassist_image_uploader",
            help="🎯 点击这里，然后 Ctrl+V 即可粘贴截图！也支持拖拽图片文件和点击 Browse 选择文件。",
            label_visibility="collapsed",
        )

    # ── Process uploaded/pasted image ──────────────────────────────
    if uploaded_file is not None:
        file_bytes = uploaded_file.getvalue()

        # Compute a hash to detect when a *new* image is uploaded
        new_hash = hash(file_bytes)
        last_hash = st.session_state.get(f"{_IMG_KEY_UPLOADED}_hash")

        if last_hash != new_hash:
            st.session_state[f"{_IMG_KEY_UPLOADED}_hash"] = new_hash
            st.session_state[_IMG_KEY_UPLOADED] = file_bytes

            # Save image to disk
            save_dir = Path(config.output.image_dir)
            save_dir.mkdir(parents=True, exist_ok=True)
            stem = uuid.uuid4().hex[:8]
            image = Image.open(BytesIO(file_bytes))
            saved_path = save_dir / f"upload_{stem}.png"
            image.save(str(saved_path))
            st.session_state[_IMG_KEY_SAVED_PATH] = str(saved_path)

            # Extract text via vision provider
            with st.spinner("🔍 正在识别图片中的题目..."):
                extracted = _extract_text_from_image(saved_path, config)
            st.session_state[_IMG_KEY_EXTRACTED] = extracted

            st.rerun()

    # ── Show the uploaded image and editable extracted text ──────────
    if st.session_state.get(_IMG_KEY_SAVED_PATH):
        extracted = st.session_state.get(_IMG_KEY_EXTRACTED, "")
        saved_path = st.session_state.get(_IMG_KEY_SAVED_PATH, "")

        col_img, col_text = st.columns([1, 2])
        with col_img:
            if Path(saved_path).exists():
                st.image(saved_path, caption="上传的图片", use_container_width=True)
        with col_text:
            st.caption("📝 识别结果（可编辑修正）：")
            corrected = st.text_area(
                "识别文本",
                value=extracted,
                height=200,
                key="_mathassist_ocr_result",
                label_visibility="collapsed",
            )
            # Update the extracted text with any user edits
            if corrected != extracted:
                st.session_state[_IMG_KEY_EXTRACTED] = corrected

            if st.button("❌ 清除图片", key="_mathassist_clear_image"):
                _clear_uploaded_image()
                st.rerun()


def _extract_text_from_image(image_path: str, config: Config) -> str:
    """Use the vision provider to extract math text from an image.

    Args:
        image_path: Path to the saved image file.
        config: Application configuration.

    Returns:
        Extracted text, or an error message prefixed with "Error:".
    """
    try:
        from math_assistant.vision_providers import get_vision_provider

        # Fall back to main API key if vision-specific key is not set
        vision_api_key = config.vision.api_key
        if vision_api_key is None:
            try:
                vision_api_key = config.get_api_key()
            except ValueError:
                pass  # will be handled by the provider's own fallback

        provider = get_vision_provider(
            config.vision.provider,
            model=config.vision.model,
            api_key=vision_api_key,
            base_url=config.vision.base_url,
        )
        result = provider.image_to_text(str(image_path))
        if result.startswith("Error:"):
            return result  # pass through the error
        return result
    except ValueError as e:
        return f"Error: Vision provider not configured — {e}"
    except Exception as e:
        return f"Error: OCR extraction failed — {e}"


def _clear_uploaded_image() -> None:
    """Clear all uploaded image state including the file_uploader widget."""
    st.session_state.pop(f"{_IMG_KEY_UPLOADED}_hash", None)
    st.session_state.pop(_IMG_KEY_UPLOADED, None)
    st.session_state.pop(_IMG_KEY_EXTRACTED, None)
    st.session_state.pop(_IMG_KEY_SAVED_PATH, None)
    # Reset the file_uploader widget so it doesn't show the old file
    st.session_state["_mathassist_image_uploader"] = None


def _build_combined_message(user_text: str) -> str:
    """Combine extracted image text with user's supplementary notes.

    Args:
        user_text: The text entered by the user in the chat input.

    Returns:
        The combined message to send to the agent.
    """
    extracted = st.session_state.get(_IMG_KEY_EXTRACTED, "")
    saved_path = st.session_state.get(_IMG_KEY_SAVED_PATH, "")

    parts: list[str] = []

    if extracted and not extracted.startswith("Error:"):
        parts.append(f"【图片中的题目】\n{extracted}")
    elif extracted and extracted.startswith("Error:"):
        # OCR failed — tell the agent to use image_to_text tool
        if saved_path:
            parts.append(
                f"[图片上传失败，OCR 服务不可用: {extracted}]\n\n"
                f"请使用 image_to_text 工具读取图片: {saved_path}"
            )
        else:
            parts.append(f"[图片识别失败: {extracted}]")

    if user_text.strip():
        if parts:
            parts.append(f"\n【补充说明】\n{user_text}")
        else:
            parts.append(user_text)

    return "\n\n".join(parts) if parts else user_text


def _handle_user_input(prompt: str, config: Config) -> None:
    """Process a user message: combine with image OCR if present, run agent, sync.

    Args:
        prompt: The user's input text.
        config: Application config.
    """
    # ── Build the combined message (image OCR + user text) ──
    combined_prompt = _build_combined_message(prompt)
    has_image = st.session_state.get(_IMG_KEY_SAVED_PATH) is not None

    # Prepare display text: show user the original input + image context
    display_text = prompt
    if has_image:
        saved_path = st.session_state.get(_IMG_KEY_SAVED_PATH, "")
        extracted = st.session_state.get(_IMG_KEY_EXTRACTED, "")
        if extracted and not extracted.startswith("Error:"):
            display_text = f"📸 *[已上传图片]*  {saved_path}\n\n{combined_prompt}"
        else:
            display_text = combined_prompt

    # Add user message to state (store the combined prompt for the agent)
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
        # Placeholder for real-time streaming
        text_placeholder = st.empty()
        tool_expanders: dict[str, st.expander] = {}

        full_response_parts: list[str] = []
        step_count = 0

        try:
            for event in run_agent_stream_cached(combined_prompt, thread_id, config):
                node = event["node"]
                msg_type = event["type"]
                content = event.get("content", "")

                step_count += 1

                if msg_type == "AIMessage" and node == "model":
                    # Show step indicator
                    st.caption(f"💭 Step {step_count}: reasoning...")
                    if content.strip():
                        full_response_parts.append(content)
                        # Render accumulated text so far (with LaTeX fix)
                        combined = "\n\n".join(full_response_parts)
                        text_placeholder.markdown(_fix_latex_delimiters(combined))
                    # ── Record assistant text for save ──
                    save_mgr.recorder.add_assistant_text(content)
                    # Record tool calls if present on the AIMessage
                    if event.get("tool_calls"):
                        for tc in event["tool_calls"]:
                            save_mgr.recorder.record_tool_call(
                                name=tc.get("name", "unknown"),
                                args=tc.get("args", {}),
                            )

                elif msg_type == "ToolMessage" and node == "tools":
                    tool_name = event.get("tool_name", "unknown")
                    # Show tool call in expander
                    with st.expander(f"🛠 {tool_name} (Step {step_count})", expanded=False):
                        tool_display = content[:3000]
                        if tool_name == "execute_python":
                            st.code(tool_display, language="python")
                        else:
                            st.text(tool_display)
                        # Render any charts generated by the tool
                        _render_tool_images(content)

                    # Record tool message for history
                    store.add_tool_message(tool_name, content[:1000])
                    # ── Record tool result for save ──
                    save_mgr.recorder.record_tool_result(
                        name=tool_name,
                        output=content,
                    )

            # Final render: all text
            final_text = "\n\n".join(full_response_parts)
            if final_text.strip():
                text_placeholder.markdown(_fix_latex_delimiters(final_text))
                store.add_assistant_message(final_text)
            else:
                text_placeholder.markdown("*(No output generated)*")

        except Exception as e:
            text_placeholder.error(f"Error: {e}")

        finally:
            # ── Auto-save: finalize turn and save question group ──
            try:
                turn = save_mgr.recorder.end_turn()
                if save_mgr.recorder.get_current_group() is not None:
                    save_mgr.recorder.add_turn_to_current_group(turn)
                    save_mgr.save_current_group()
            except Exception:
                pass  # best-effort: don't break the UI on save failure

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
