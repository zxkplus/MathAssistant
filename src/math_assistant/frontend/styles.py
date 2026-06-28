"""Design token system and CSS for MathAssistant frontend.

Design direction: "数学花园" (Mathematical Garden) — warm, vibrant, organic.
Mathematics reimagined as an inviting garden of ideas rather than a cold,
sterile workspace.

Color palette: warm paper + vibrant accent highlights (coral, ocean, marigold).
Typography: serif headings for mathematical elegance, sans-serif body for readability.
Signature: graph-paper grid background + hand-annotated code blocks.
"""

from __future__ import annotations

import textwrap

# ── Design Tokens ──────────────────────────────────────────────────────────
# All visual constants in one place — change the look by editing these only.

TOKENS = {
    # ── Core palette ──
    "canvas": "#FFFDF7",          # main background — warm paper
    "surface": "#FFFFFF",          # card / message bubble surface
    "surface_warm": "#FDF9F0",     # warm tinted surface (assistant messages)
    "ink": "#1C1A26",             # primary text — deep but warm
    "ink_soft": "#5C5A66",        # secondary text — softer graphite
    "ink_muted": "#9D9BA6",       # tertiary text — muted
    "border": "#E8E4DB",          # warm border — not harsh gray
    "border_light": "#F2EEE7",    # very subtle border

    # ── Accent colors (the "highlighters") ──
    "coral": "#F85A4A",           # primary accent — energy, CTAs, user messages
    "coral_light": "#FFF0EE",     # coral tint background
    "ocean": "#149DAA",           # secondary accent — tools, code, precision
    "ocean_light": "#EBF9FA",     # ocean tint background
    "marigold": "#F5A623",        # highlight — thinking, warnings, discovery
    "marigold_light": "#FFF8EC",  # marigold tint background
    "periwinkle": "#5B5FEE",      # links, creative/academic elements
    "periwinkle_light": "#F0F0FE",# periwinkle tint
    "sage": "#5CAD6C",            # success / correct answers
    "sage_light": "#EDF7EF",      # sage tint
    "rose": "#E5534B",            # errors / warnings
    "rose_light": "#FEF0EF",      # rose tint

    # ── Semantic mappings ──
    "user_bubble_bg": "#FFF0EE",  # user message — coral tint
    "user_bubble_border": "#FECAC3",
    "assistant_bubble_bg": "#FFFFFF",
    "assistant_bubble_border": "#E8E4DB",
    "tool_bg": "#F5F9FB",         # tool execution — cool tint
    "tool_border": "#D4E8EC",
    "code_bg": "#F3F6F8",
    "sidebar_bg": "#FBFAF5",      # sidebar — slightly warmer paper
    "sidebar_hover": "#F3F0E7",
}

# ── Typography ──────────────────────────────────────────────────────────────

FONT_DISPLAY = '"Georgia", "Noto Serif SC", "STSong", "SimSun", serif'
FONT_BODY = '"Inter", "Noto Sans SC", "PingFang SC", "Microsoft YaHei", system-ui, sans-serif'
FONT_CODE = '"JetBrains Mono", "Fira Code", "Cascadia Code", "Consolas", "Monaco", monospace'

# ── Radii / spacing ─────────────────────────────────────────────────────────

RADIUS_SM = "6px"
RADIUS_MD = "10px"
RADIUS_LG = "16px"
RADIUS_XL = "24px"

# ── Shadows ─────────────────────────────────────────────────────────────────

SHADOW_CARD = "0 1px 2px rgba(28, 26, 38, 0.04), 0 1px 6px rgba(28, 26, 38, 0.06)"
SHADOW_ELEVATED = "0 2px 4px rgba(28, 26, 38, 0.06), 0 4px 16px rgba(28, 26, 38, 0.08)"
SHADOW_GLOW_CORAL = "0 0 0 3px rgba(248, 90, 74, 0.12)"
SHADOW_GLOW_OCEAN = "0 0 0 3px rgba(20, 157, 170, 0.12)"


# ── Global CSS ──────────────────────────────────────────────────────────────
# Injected once at app startup via st.markdown(..., unsafe_allow_html=True).

def get_global_css() -> str:
    """Return the complete global CSS stylesheet for MathAssistant.

    Includes:
    - Custom properties (:root) for all design tokens
    - Graph-paper background pattern
    - Chat message bubble styling
    - Tool execution panel styling
    - Sidebar refinements
    - Button / input overrides
    - Animation keyframes
    - Scrollbar styling
    - Dark mode overrides
    """
    t = TOKENS  # shorthand

    return f"""
    /* ═══════════════════════════════════════════════════════════════════════
       MathAssistant — Mathematical Garden
       Design tokens, layout, components, animations
       ═══════════════════════════════════════════════════════════════════════ */

    /* ── CSS Custom Properties ──────────────────────────────────────────── */
    :root {{
        /* Palette */
        --ma-canvas: {t['canvas']};
        --ma-surface: {t['surface']};
        --ma-surface-warm: {t['surface_warm']};
        --ma-ink: {t['ink']};
        --ma-ink-soft: {t['ink_soft']};
        --ma-ink-muted: {t['ink_muted']};
        --ma-border: {t['border']};
        --ma-border-light: {t['border_light']};
        --ma-coral: {t['coral']};
        --ma-coral-light: {t['coral_light']};
        --ma-ocean: {t['ocean']};
        --ma-ocean-light: {t['ocean_light']};
        --ma-marigold: {t['marigold']};
        --ma-marigold-light: {t['marigold_light']};
        --ma-periwinkle: {t['periwinkle']};
        --ma-periwinkle-light: {t['periwinkle_light']};
        --ma-sage: {t['sage']};
        --ma-sage-light: {t['sage_light']};
        --ma-rose: {t['rose']};
        --ma-rose-light: {t['rose_light']};

        /* Typography */
        --ma-font-display: {FONT_DISPLAY};
        --ma-font-body: {FONT_BODY};
        --ma-font-code: {FONT_CODE};

        /* Radii */
        --ma-radius-sm: {RADIUS_SM};
        --ma-radius-md: {RADIUS_MD};
        --ma-radius-lg: {RADIUS_LG};
        --ma-radius-xl: {RADIUS_XL};

        /* Shadows */
        --ma-shadow-card: {SHADOW_CARD};
        --ma-shadow-elevated: {SHADOW_ELEVATED};
    }}

    /* ── Global resets & base ──────────────────────────────────────────── */
    .stApp {{
        background-color: var(--ma-canvas);
    }}

    .stApp > header {{
        background-color: var(--ma-canvas);
    }}

    /* Subtle graph-paper texture on main area */
    .main .block-container {{
        background-image:
            linear-gradient(rgba(28, 26, 38, 0.015) 1px, transparent 1px),
            linear-gradient(90deg, rgba(28, 26, 38, 0.015) 1px, transparent 1px);
        background-size: 24px 24px;
        background-position: -1px -1px;
        padding-top: 1.5rem;
    }}

    /* ── Typography overrides ──────────────────────────────────────────── */
    h1, h2, h3, h4, h5, h6 {{
        font-family: var(--ma-font-display) !important;
        color: var(--ma-ink) !important;
        letter-spacing: -0.01em;
    }}

    h1 {{ font-weight: 700; }}
    h2 {{ font-weight: 600; }}
    h3 {{ font-weight: 600; font-size: 1.1rem !important; }}

    p, li, span, div, label, caption {{
        font-family: var(--ma-font-body);
        color: var(--ma-ink-soft);
    }}

    code {{
        font-family: var(--ma-font-code) !important;
        font-size: 0.875em !important;
    }}

    a {{
        color: var(--ma-periwinkle) !important;
        text-decoration: none;
        transition: color 0.15s ease;
    }}
    a:hover {{
        color: var(--ma-ocean) !important;
        text-decoration: underline;
    }}

    /* ── Chat messages — user bubble ───────────────────────────────────── */
    [data-testid="stChatMessage"] {{
        margin-bottom: 0.75rem;
    }}

    /* User message: warm coral accent */
    [data-testid="stChatMessage"] [data-testid="stChatMessageAvatar"]:has(+ *) {{
        /* We target user messages via the chat_message("user") */
    }}

    /* Assistant message container */
    .stChatMessage:has([data-testid="chat-avatar-assistant"]) {{
        /* No extra styling needed — assistant gets clean surface */
    }}

    /* ── Chat input ─────────────────────────────────────────────────────── */
    [data-testid="stChatInput"] {{
        position: sticky;
        bottom: 0;
    }}

    [data-testid="stChatInput"] textarea {{
        border: 2px solid var(--ma-border) !important;
        border-radius: var(--ma-radius-lg) !important;
        font-family: var(--ma-font-body) !important;
        font-size: 0.95rem !important;
        padding: 0.75rem 1rem !important;
        transition: border-color 0.2s ease, box-shadow 0.2s ease;
        background: var(--ma-surface) !important;
    }}

    [data-testid="stChatInput"] textarea:focus {{
        border-color: var(--ma-coral) !important;
        box-shadow: {SHADOW_GLOW_CORAL} !important;
        outline: none !important;
    }}

    /* ── Expanders (tool panels) ────────────────────────────────────────── */
    [data-testid="stExpander"] {{
        border: 1px solid var(--ma-border) !important;
        border-radius: var(--ma-radius-md) !important;
        background: {t['tool_bg']} !important;
        margin-bottom: 0.5rem;
        overflow: hidden;
        transition: border-color 0.2s ease, box-shadow 0.2s ease;
    }}

    [data-testid="stExpander"]:hover {{
        border-color: var(--ma-ocean) !important;
        box-shadow: {SHADOW_GLOW_OCEAN};
    }}

    [data-testid="stExpander"] details summary {{
        font-family: var(--ma-font-body);
        font-size: 0.85rem;
        font-weight: 500;
        color: var(--ma-ocean) !important;
        padding: 0.5rem 0.75rem;
    }}

    [data-testid="stExpander"] details summary:hover {{
        color: var(--ma-coral) !important;
    }}

    /* ── Code blocks ────────────────────────────────────────────────────── */
    .stCodeBlock, [data-testid="stCodeBlock"] {{
        border-radius: var(--ma-radius-md) !important;
        border: 1px solid var(--ma-border-light) !important;
    }}

    .stCodeBlock pre, [data-testid="stCodeBlock"] pre {{
        background: {t['code_bg']} !important;
        font-family: var(--ma-font-code) !important;
        font-size: 0.82rem !important;
    }}

    /* ── Buttons — primary ──────────────────────────────────────────────── */
    .stButton > button {{
        border-radius: var(--ma-radius-md) !important;
        font-family: var(--ma-font-body) !important;
        font-weight: 500 !important;
        font-size: 0.875rem !important;
        transition: all 0.2s ease !important;
        border: 1px solid transparent !important;
    }}

    .stButton > button[kind="primary"] {{
        background: var(--ma-coral) !important;
        color: white !important;
        border-color: var(--ma-coral) !important;
    }}

    .stButton > button[kind="primary"]:hover {{
        background: #E04A3C !important;
        border-color: #E04A3C !important;
        box-shadow: {SHADOW_GLOW_CORAL};
        transform: translateY(-1px);
    }}

    .stButton > button[kind="primary"]:active {{
        transform: translateY(0);
    }}

    .stButton > button[kind="secondary"] {{
        background: var(--ma-surface) !important;
        color: var(--ma-ink-soft) !important;
        border-color: var(--ma-border) !important;
    }}

    .stButton > button[kind="secondary"]:hover {{
        border-color: var(--ma-ocean) !important;
        color: var(--ma-ocean) !important;
    }}

    /* ── Sidebar ────────────────────────────────────────────────────────── */
    [data-testid="stSidebar"] {{
        background: {t['sidebar_bg']} !important;
        border-right: 1px solid var(--ma-border) !important;
    }}

    [data-testid="stSidebar"] .stButton > button {{
        text-align: left !important;
        border-radius: var(--ma-radius-md) !important;
        font-size: 0.85rem !important;
        font-weight: 400 !important;
        transition: all 0.15s ease;
    }}

    [data-testid="stSidebar"] .stButton > button:hover {{
        background: {t['sidebar_hover']} !important;
        transform: translateX(2px);
    }}

    [data-testid="stSidebar"] hr {{
        border-color: var(--ma-border-light) !important;
        margin: 1rem 0 !important;
    }}

    /* ── Metrics (sidebar stats) ────────────────────────────────────────── */
    [data-testid="stMetric"] {{
        background: var(--ma-surface) !important;
        border: 1px solid var(--ma-border-light) !important;
        border-radius: var(--ma-radius-md) !important;
        padding: 0.75rem !important;
        margin-bottom: 0.5rem;
        transition: box-shadow 0.2s ease;
    }}

    [data-testid="stMetric"]:hover {{
        box-shadow: var(--ma-shadow-elevated);
    }}

    [data-testid="stMetric"] label {{
        font-family: var(--ma-font-body) !important;
        font-size: 0.75rem !important;
        color: var(--ma-ink-muted) !important;
    }}

    [data-testid="stMetricValue"] {{
        font-family: var(--ma-font-display) !important;
        font-size: 1.5rem !important;
        font-weight: 700 !important;
        color: var(--ma-ink) !important;
    }}

    /* ── Forms (auth page) ──────────────────────────────────────────────── */
    [data-testid="stForm"] {{
        background: var(--ma-surface) !important;
        border: 1px solid var(--ma-border) !important;
        border-radius: var(--ma-radius-lg) !important;
        padding: 1.5rem !important;
        box-shadow: var(--ma-shadow-card);
    }}

    /* Input fields */
    .stTextInput input, [data-testid="stTextInput"] input {{
        border: 2px solid var(--ma-border) !important;
        border-radius: var(--ma-radius-md) !important;
        font-family: var(--ma-font-body) !important;
        padding: 0.6rem 0.8rem !important;
        transition: border-color 0.2s ease, box-shadow 0.2s ease;
    }}

    .stTextInput input:focus, [data-testid="stTextInput"] input:focus {{
        border-color: var(--ma-coral) !important;
        box-shadow: {SHADOW_GLOW_CORAL} !important;
        outline: none !important;
    }}

    /* ── File uploader ──────────────────────────────────────────────────── */
    [data-testid="stFileUploader"] {{
        border: 2px dashed var(--ma-border) !important;
        border-radius: var(--ma-radius-lg) !important;
        padding: 1.5rem !important;
        text-align: center;
        transition: border-color 0.2s ease, background 0.2s ease;
        background: {t['surface_warm']} !important;
    }}

    [data-testid="stFileUploader"]:hover {{
        border-color: var(--ma-ocean) !important;
        background: {t['ocean_light']} !important;
    }}

    [data-testid="stFileUploader"]:focus-within {{
        border-color: var(--ma-coral) !important;
        box-shadow: {SHADOW_GLOW_CORAL};
    }}

    /* Upload zone drop area */
    [data-testid="stFileUploader"] section {{
        border: none !important;
    }}

    /* ── Tabs ───────────────────────────────────────────────────────────── */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 0.25rem;
        border-bottom: 2px solid var(--ma-border-light) !important;
    }}

    .stTabs [data-baseweb="tab"] {{
        font-family: var(--ma-font-body) !important;
        font-size: 0.875rem !important;
        font-weight: 500 !important;
        border-radius: var(--ma-radius-md) var(--ma-radius-md) 0 0 !important;
        transition: all 0.15s ease;
    }}

    .stTabs [data-baseweb="tab"]:hover {{
        color: var(--ma-coral) !important;
    }}

    .stTabs [data-baseweb="tab"][aria-selected="true"] {{
        color: var(--ma-coral) !important;
        border-bottom: 3px solid var(--ma-coral) !important;
    }}

    /* ── Dividers ───────────────────────────────────────────────────────── */
    hr {{
        border-color: var(--ma-border) !important;
        margin: 0.75rem 0 !important;
    }}

    /* ── Image upload container ──────────────────────────────────────────── */
    [data-testid="stVerticalBlockBorderWrapper"] {{
        border: 2px dashed var(--ma-border) !important;
        border-radius: var(--ma-radius-lg) !important;
    }}

    /* ── Spinner / progress ─────────────────────────────────────────────── */
    .stSpinner {{
        color: var(--ma-coral) !important;
    }}

    /* ── Tooltips ────────────────────────────────────────────────────────── */
    [data-baseweb="tooltip"] {{
        font-family: var(--ma-font-body) !important;
        font-size: 0.8rem !important;
        border-radius: var(--ma-radius-sm) !important;
    }}

    /* ── Success / Warning / Error messages ──────────────────────────────── */
    .stSuccess {{
        background: var(--ma-sage-light) !important;
        border-left: 4px solid var(--ma-sage) !important;
        border-radius: var(--ma-radius-md) !important;
        color: var(--ma-ink) !important;
    }}

    .stWarning {{
        background: var(--ma-marigold-light) !important;
        border-left: 4px solid var(--ma-marigold) !important;
        border-radius: var(--ma-radius-md) !important;
        color: var(--ma-ink) !important;
    }}

    .stError {{
        background: var(--ma-rose-light) !important;
        border-left: 4px solid var(--ma-rose) !important;
        border-radius: var(--ma-radius-md) !important;
        color: var(--ma-ink) !important;
    }}

    .stInfo {{
        background: var(--ma-periwinkle-light) !important;
        border-left: 4px solid var(--ma-periwinkle) !important;
        border-radius: var(--ma-radius-md) !important;
        color: var(--ma-ink) !important;
    }}

    /* ── Animations ─────────────────────────────────────────────────────── */
    @keyframes ma-fade-in {{
        from {{ opacity: 0; transform: translateY(8px); }}
        to   {{ opacity: 1; transform: translateY(0); }}
    }}

    @keyframes ma-pulse-soft {{
        0%, 100% {{ opacity: 1; }}
        50%      {{ opacity: 0.5; }}
    }}

    @keyframes ma-slide-in-left {{
        from {{ opacity: 0; transform: translateX(-12px); }}
        to   {{ opacity: 1; transform: translateX(0); }}
    }}

    @keyframes ma-ink-spread {{
        from {{ clip-path: circle(0% at 50% 50%); }}
        to   {{ clip-path: circle(100% at 50% 50%); }}
    }}

    .ma-animate-in {{
        animation: ma-fade-in 0.35s ease-out both;
    }}

    .ma-thinking {{
        animation: ma-pulse-soft 1.6s ease-in-out infinite;
    }}

    /* ── Scrollbar ──────────────────────────────────────────────────────── */
    ::-webkit-scrollbar {{
        width: 6px;
        height: 6px;
    }}

    ::-webkit-scrollbar-track {{
        background: transparent;
    }}

    ::-webkit-scrollbar-thumb {{
        background: var(--ma-border);
        border-radius: 3px;
    }}

    ::-webkit-scrollbar-thumb:hover {{
        background: var(--ma-ink-muted);
    }}

    /* ── Dark mode ──────────────────────────────────────────────────────── */
    @media (prefers-color-scheme: dark) {{
        :root {{
            --ma-canvas: #1A1920;
            --ma-surface: #24232A;
            --ma-surface-warm: #28272E;
            --ma-ink: #E8E6ED;
            --ma-ink-soft: #B8B6C0;
            --ma-ink-muted: #7A7884;
            --ma-border: #363440;
            --ma-border-light: #2E2C36;
        }}

        .main .block-container {{
            background-image:
                linear-gradient(rgba(232, 230, 237, 0.02) 1px, transparent 1px),
                linear-gradient(90deg, rgba(232, 230, 237, 0.02) 1px, transparent 1px);
        }}

        [data-testid="stExpander"] {{
            background: #1E1D26 !important;
        }}

        .stCodeBlock pre, [data-testid="stCodeBlock"] pre {{
            background: #1E1D26 !important;
        }}

        [data-testid="stSidebar"] {{
            background: #1E1D26 !important;
        }}

        [data-testid="stFileUploader"] {{
            background: #1E1D26 !important;
        }}

        [data-testid="stMetric"] {{
            background: var(--ma-surface) !important;
        }}
    }}

    /* ── Responsive ──────────────────────────────────────────────────────── */
    @media (max-width: 640px) {{
        .main .block-container {{
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
        }}

        [data-testid="stExpander"] details summary {{
            font-size: 0.8rem;
        }}
    }}

    /* ── Print ──────────────────────────────────────────────────────────── */
    @media print {{
        .stApp {{
            background: white !important;
        }}
        [data-testid="stSidebar"] {{
            display: none !important;
        }}
        .main .block-container {{
            background-image: none !important;
            max-width: 100% !important;
        }}
    }}

    /* ── Focus visible (accessibility) ──────────────────────────────────── */
    :focus-visible {{
        outline: 2px solid var(--ma-coral) !important;
        outline-offset: 2px;
        border-radius: var(--ma-radius-sm);
    }}

    /* ── Reduced motion (accessibility) ─────────────────────────────────── */
    @media (prefers-reduced-motion: reduce) {{
        *, *::before, *::after {{
            animation-duration: 0.01ms !important;
            animation-iteration-count: 1 !important;
            transition-duration: 0.01ms !important;
        }}
    }}
    """


# ── Inline style helpers (for one-off HTML injection in specific pages) ────

def get_welcome_html() -> str:
    """Styled welcome message shown when the chat is empty."""
    t = TOKENS
    return textwrap.dedent(f"""
    <div style="text-align: center; padding: 2rem 1rem; animation: ma-fade-in 0.5s ease-out both;">
        <div style="font-family: {FONT_DISPLAY}; font-size: 2.5rem; font-weight: 700; color: {t['ink']}; margin-bottom: 0.5rem;">
            🧮 数学花园
        </div>
        <p style="font-family: {FONT_BODY}; font-size: 1rem; color: {t['ink_soft']}; margin-bottom: 1.5rem;">
            Mathematical Garden — 探索数学之美的 AI 导师
        </p>
        <div style="display: flex; flex-wrap: wrap; gap: 0.5rem; justify-content: center; margin-bottom: 1.5rem;">
            {_tag("📐 方程求解", t['coral'], t['coral_light'])}
            {_tag("📊 函数绘图", t['ocean'], t['ocean_light'])}
            {_tag("📖 概念讲解", t['periwinkle'], t['periwinkle_light'])}
            {_tag("🔍 资料搜索", t['marigold'], t['marigold_light'])}
            {_tag("📸 题目识别", t['sage'], t['sage_light'])}
        </div>
        <p style="font-family: {FONT_BODY}; font-size: 0.9rem; color: {t['ink_muted']};">
            试试问我一个问题，或者直接粘贴一张题目图片吧！
        </p>
    </div>
    """).strip()


def get_auth_header_html() -> str:
    """Styled header for the auth page."""
    t = TOKENS
    return textwrap.dedent(f"""
    <div style="text-align: center; margin-bottom: 2rem;">
        <div style="font-family: {FONT_DISPLAY}; font-size: 2.2rem; font-weight: 700; color: {t['ink']}; margin-bottom: 0.25rem;">
            🧮 MathAssistant
        </div>
        <p style="font-family: {FONT_BODY}; font-size: 0.95rem; color: {t['ink_soft']}; margin: 0;">
            AI-Powered Mathematics Teacher
        </p>
    </div>
    """).strip()


def _tag(label: str, color: str, bg: str) -> str:
    """Build a single styled tag/chip."""
    return textwrap.dedent(f"""
    <span style="display: inline-block; font-family: {FONT_BODY}; font-size: 0.8rem; padding: 0.3rem 0.7rem; border-radius: 20px; color: {color}; background: {bg}; border: 1px solid {color}20;">{label}</span>
    """).strip()


def get_tool_panel_css(tool_name: str) -> str:
    """Return inline CSS for a tool-specific panel accent.

    Args:
        tool_name: The name of the tool (execute_python, web_search, etc.)

    Returns:
        CSS accent color for the given tool type.
    """
    tool_colors = {
        "execute_python": TOKENS["ocean"],
        "web_search": TOKENS["sage"],
        "image_to_text": TOKENS["periwinkle"],
        "search_papers": TOKENS["marigold"],
    }
    return tool_colors.get(tool_name, TOKENS["ink_soft"])
