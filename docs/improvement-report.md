# MathAssistant 改进报告

> 日期: 2026-06-24 | 版本: v1.0

---

## 目录

1. [会话保存为 Markdown 文件](#1-会话保存为-markdown-文件)
2. [数学公式终端渲染优化](#2-数学公式终端渲染优化)
3. [图表在终端内显示](#3-图表在终端内显示)
4. [其他改进建议](#4-其他改进建议)
5. [实施优先级建议](#5-实施优先级建议)

---

## 1. 会话保存为 Markdown 文件

### 1.1 现状

当前每次对话仅在终端实时显示，关闭后所有内容丢失。虽然图表文件保存在 `images/` 目录，但没有与之关联的对话上下文。

### 1.2 设计方案

#### 整体架构

新增 `SessionRecorder` 模块，在 REPL 循环中记录每一轮对话，会话结束时自动生成格式精美的 Markdown 文件。

```
src/math_assistant/
├── session/
│   ├── __init__.py
│   ├── recorder.py      # SessionRecorder: 记录对话轮次
│   └── exporter.py      # MarkdownExporter: 生成 MD 文件
```

#### Markdown 文件结构

```markdown
---
title: "求解 x² - 5x + 6 = 0"
date: 2026-06-24 15:20:00
session_id: a1b2c3d4
model: deepseek-chat
---

# 🧮 MathAssistant 会话记录

**会话 ID**: `a1b2c3d4`
**日期**: 2026-06-24 15:20:00
**模型**: deepseek-chat

---

## Q1: 求解 x² - 5x + 6 = 0

**时间**: 15:20:05

### 📝 回答

方程 $x^2 - 5x + 6 = 0$ 可以通过因式分解求解：

$$x^2 - 5x + 6 = (x-2)(x-3) = 0$$

因此解为 $x = 2$ 或 $x = 3$。

### 🔧 工具调用

<details>
<summary>execute_python — 验证结果</summary>

```python
import sympy as sp
x = sp.symbols('x')
sol = sp.solve(x**2 - 5*x + 6, x)
print(sol)  # [2, 3]
```

**输出:**
```
[2, 3]
```
</details>

### 📊 图表

![解的几何意义](images/quadratic_plot.png)

*图: 二次函数 y = x² - 5x + 6 的图像，与 x 轴的交点即为方程的解*

---

## Q2: 绘制 sin(x)/x 的图像

...

---
*由 MathAssistant 自动生成*
```

#### 关键设计点

| 特性 | 说明 |
|------|------|
| **YAML Frontmatter** | 包含元数据，方便索引和搜索 |
| **折叠的工具调用** | 使用 `<details>` 标签，默认收起，保持可读性 |
| **图表自动嵌入** | 自动检测 `images/*.png` 引用并转为 `![](path)` |
| **LaTeX 数学公式** | 保留 `$...$` 和 `$$...$$`，在 VS Code / GitHub / Typora 中完美渲染 |
| **多图表支持** | 每张图表单独一个 `###` 小节，带说明文字 |
| **中英文混排** | 完美支持中英文混排 |

#### 实现要点

```python
# src/math_assistant/session/recorder.py

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

@dataclass
class Turn:
    """单轮对话记录"""
    question: str
    answer: str
    tool_calls: list[dict]       # {name, input, output}
    images: list[str]             # 相对路径, 如 "images/plot.png"
    timestamp: datetime

@dataclass
class Session:
    """完整会话"""
    session_id: str
    model: str
    turns: list[Turn] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

    def add_turn(self, turn: Turn):
        self.turns.append(turn)
```

```python
# src/math_assistant/session/exporter.py

class MarkdownExporter:
    """将 Session 导出为格式精美的 Markdown 文件"""

    def __init__(self, output_dir: str = "./sessions"):
        self.output_dir = Path(output_dir)

    def export(self, session: Session) -> Path:
        """导出会话为 .md 文件，返回文件路径"""
        ...
```

#### 触发时机

提供三种保存模式，通过配置项 `output.save_mode` 控制：

| 模式 | 行为 |
|------|------|
| `"session"` (推荐) | 会话结束（`quit`）时保存整个会话 |
| `"turn"` | 每轮问答单独保存一个 md 文件 |
| `"manual"` | 用户输入 `save` 命令手动保存 |

#### CLI 新增命令

```
save              — 手动保存当前会话
save --path xxx   — 保存到指定路径
export html       — 导出为 HTML (带 MathJax)
```

---

## 2. 数学公式终端渲染优化

### 2.1 问题分析

当前使用 `rich.Markdown()` 渲染回答，但 Rich 的 Markdown 渲染器**完全不支持 LaTeX 数学公式**。用户看到的是原始 LaTeX 源码：

```
当前显示: 方程 $x^2 - 5x + 6 = 0$ 的解为 $x = 2$ 或 $x = 3$
期望效果: 方程 x² − 5x + 6 = 0 的解为 x = 2 或 x = 3  (美化的)
```

### 2.2 可选方案对比

#### 方案 A: Unicode 数学符号映射（推荐用作基础层）

将常见 LaTeX 公式转换为 Unicode 数学字符，终端可直接显示。

| LaTeX | Unicode | 效果 |
|-------|---------|------|
| `x^2` | x² | 上标数字 |
| `x_i` | xᵢ | 下标 |
| `\sqrt{x}` | √x | 根号 |
| `\int` | ∫ | 积分 |
| `\sum` | ∑ | 求和 |
| `\pi` | π | 圆周率 |
| `\alpha, \beta` | α, β | 希腊字母 |
| `\infty` | ∞ | 无穷 |
| `\pm` | ± | 正负 |
| `\cdot` | · | 点乘 |
| `\times` | × | 叉乘 |
| `\frac{a}{b}` | (a)/(b) 或 ᵃ/₆ | 分数（有限支持） |
| `\leq, \geq` | ≤, ≥ | 不等号 |
| `\to, \rightarrow` | → | 箭头 |

**库选择**：

| 库 | 优点 | 缺点 |
|----|------|------|
| **[`latex2unicode`](https://pypi.org/project/latex2unicode/)** | 专门做 LaTeX→Unicode 转换，处理大部分常见公式 | 复杂公式可能不完美 |
| **[`unicodedata`](https://docs.python.org/3/library/unicodedata.html)** (内置) | 零依赖，可手动构建映射表 | 需自行维护映射 |
| **[`pylatexenc`](https://pypi.org/project/pylatexenc/)** | 完整的 LaTeX 解析器 | 偏重，主要用于解析而非渲染 |

**推荐**: `latex2unicode` + 自定义 fallback 映射表。

#### 方案 B: SymPy Pretty Printing（用于计算结果的辅助渲染）

SymPy 原生支持 Unicode/ASCII pretty printing：

```python
from sympy import symbols, Integral, sqrt, sin, init_printing
init_printing(use_unicode=True)

x = symbols('x')
expr = Integral(sqrt(1/x), x)
# sympy.pprint(expr) 会输出:
# ⌠
# ⎮     ___
# ⎮    ╱ 1
# ⎮   ╱  ─  dx
# ⎮ ╲╱   x
# ⌡
```

**适用场景**: 当工具调用 `execute_python` 返回表达式时，可以自动 pretty print。

#### 方案 C: 终端内嵌图片渲染（高级方案）

在支持图片协议的终端（iTerm2, Kitty, WezTerm）中，将 LaTeX 渲染为图片并内联显示。

**实现路径**:
1. LaTeX → MathJax/KaTeX → SVG/PNG（需要 Node.js）或
2. LaTeX → matplotlib mathtext → PNG（已有 matplotlib 依赖）
3. PNG → 终端图片协议（iTerm2 的 `imgcat`, Kitty 的 `icat`）

**Python 库**: `term-image`, `timg`, `kitty-icat`

```python
# 伪代码示例
import matplotlib.pyplot as plt
import io

def latex_to_terminal_image(latex: str) -> str:
    """将 LaTeX 渲染为终端内嵌图片"""
    fig, ax = plt.subplots(figsize=(6, 0.5))
    ax.text(0.5, 0.5, f"${latex}$", transform=ax.transAxes,
            fontsize=14, ha='center', va='center')
    ax.axis('off')

    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight',
                transparent=True)
    plt.close(fig)

    # 使用终端图片协议显示
    from term_image import from_image
    return from_image(buf.getvalue())
```

**限制**: 仅在支持的终端中有效，普通终端（如系统自带 Terminal）不支持。

#### 方案 D: Rich 自定义渲染（实用折中）

重写 Rich 的 Markdown 渲染钩子，对数学公式块做特殊处理：

```python
from rich.markdown import Markdown
from rich.text import Text
from rich.style import Style
import re

class MathMarkdown(Markdown):
    """支持数学公式高亮的 Rich Markdown 渲染器"""

    MATH_STYLE = Style(color="cyan", italic=True)

    def __init__(self, markup, **kwargs):
        # 预处理: 给 LaTeX 公式包裹特殊标记
        markup = self._preprocess_math(markup)
        super().__init__(markup, **kwargs)

    @staticmethod
    def _preprocess_math(text: str) -> str:
        # 将 $...$ 包裹在特殊样式中
        text = re.sub(r'\$\$(.+?)\$\$', r'[cyan italic]$$\1$$[/]', text)
        text = re.sub(r'\$(.+?)\$', r'[cyan italic]$\1$[/]', text)
        return text
```

**效果**: 数学公式在终端中以青色斜体显示，虽然没有真正的数学排版，但至少能在视觉上区别于普通文字。

### 2.3 推荐方案组合

采用**分层策略**，根据终端能力自动降级：

```
┌──────────────────────────────────────────────┐
│  第 1 层: 检测终端能力                        │
│  - 是否支持图片协议? (iTerm2/Kitty/WezTerm)   │
│  - 是否支持 Unicode?                          │
│  - 是否支持 24-bit 颜色?                      │
├──────────────────────────────────────────────┤
│  第 2 层: 选择渲染策略                        │
│                                               │
│  图片终端 ──→ LaTeX → mathtext → PNG → 内嵌   │
│  Unicode终端 → LaTeX → latex2unicode          │
│  普通终端  ──→ 原始 LaTeX + 颜色高亮           │
│                                               │
│  同时: SymPy 表达式 → sympy.pprint()           │
├──────────────────────────────────────────────┤
│  第 3 层: 保存到 MD 文件                       │
│  - 全部保留标准 LaTeX 语法 $...$              │
│  - VS Code / GitHub / Typora 完美渲染          │
└──────────────────────────────────────────────┘
```

### 2.4 具体实现计划

```python
# src/math_assistant/ui/renderer.py (新文件)

from enum import Enum
from typing import Optional

class TerminalCapability(Enum):
    IMAGE = "image"        # iTerm2, Kitty, WezTerm
    UNICODE = "unicode"    # 大多数现代终端
    PLAIN = "plain"        # 基础终端

class MathRenderer:
    """数学公式渲染器 — 根据终端能力自动选择策略"""

    def __init__(self):
        self.capability = self._detect_capability()

    def _detect_capability(self) -> TerminalCapability:
        """检测终端能力"""
        term = os.environ.get("TERM", "")
        term_program = os.environ.get("TERM_PROGRAM", "")

        # Kitty
        if "KITTY_WINDOW_ID" in os.environ:
            return TerminalCapability.IMAGE
        # iTerm2
        if term_program == "iTerm.app" or "ITERM_SESSION_ID" in os.environ:
            return TerminalCapability.IMAGE
        # WezTerm
        if term_program == "WezTerm":
            return TerminalCapability.IMAGE
        # 检查 Unicode 支持
        if os.environ.get("LANG", "").endswith("UTF-8"):
            return TerminalCapability.UNICODE
        return TerminalCapability.PLAIN

    def render_inline_math(self, latex: str) -> str:
        """渲染行内公式 $...$"""
        if self.capability == TerminalCapability.IMAGE:
            return self._to_terminal_image(latex, inline=True)
        elif self.capability == TerminalCapability.UNICODE:
            return self._latex_to_unicode(latex)
        else:
            return f"[cyan italic]{latex}[/]"

    def render_block_math(self, latex: str) -> str:
        """渲染块级公式 $$...$$"""
        if self.capability == TerminalCapability.IMAGE:
            return self._to_terminal_image(latex, inline=False)
        elif self.capability == TerminalCapability.UNICODE:
            return self._latex_to_unicode(latex)
        else:
            return f"[bold cyan]{latex}[/]"

    @staticmethod
    def _latex_to_unicode(latex: str) -> str:
        """将 LaTeX 转换为 Unicode"""
        try:
            from latex2unicode import latex2unicode
            return latex2unicode(latex)
        except ImportError:
            # Fallback: 手动替换常见符号
            replacements = {
                r'\pi': 'π', r'\alpha': 'α', r'\beta': 'β',
                r'\gamma': 'γ', r'\theta': 'θ', r'\lambda': 'λ',
                r'\infty': '∞', r'\sqrt': '√', r'\int': '∫',
                r'\sum': '∑', r'\prod': '∏', r'\pm': '±',
                r'\leq': '≤', r'\geq': '≥', r'\neq': '≠',
                r'\approx': '≈', r'\equiv': '≡', r'\cdot': '·',
                r'\times': '×', r'\div': '÷', r'\to': '→',
                r'\Rightarrow': '⇒', r'\Leftrightarrow': '⇔',
                r'\partial': '∂', r'\nabla': '∇', r'\forall': '∀',
                r'\exists': '∃', r'\in': '∈', r'\notin': '∉',
                r'\subset': '⊂', r'\cup': '∪', r'\cap': '∩',
            }
            result = latex
            for k, v in replacements.items():
                result = result.replace(k, v)
            return result

    @staticmethod
    def _to_terminal_image(latex: str, inline: bool = False) -> str:
        """渲染为终端图片 (iTerm2/Kitty)"""
        # 使用 matplotlib mathtext 渲染
        ...
```

### 2.5 依赖新增

```toml
# pyproject.toml 新增
"latex2unicode>=0.1.0",     # LaTeX → Unicode 转换 (纯 Python, 轻量)
"term-image>=0.7.0",        # 终端图片显示 (可选, 仅高级终端)
```

---

## 3. 图表在终端内显示

### 3.1 现状

当前图表由 `execute_python` 工具生成并保存到 `images/` 目录。用户在终端中**看不到图片**，只能看到文件路径的文本提示。

### 3.2 方案

#### 方案 A: 终端图片协议（推荐主流终端用户）

利用 iTerm2/Kitty/WezTerm 的原生图片显示能力：

```python
# src/math_assistant/ui/image_display.py

import os
import subprocess
import base64
from pathlib import Path

def display_image_in_terminal(image_path: str) -> bool:
    """在终端中显示图片，返回是否成功"""
    path = Path(image_path)
    if not path.exists():
        return False

    # 检测终端类型并选择合适的协议
    if "KITTY_WINDOW_ID" in os.environ:
        return _kitty_icat(path)
    elif "ITERM_SESSION_ID" in os.environ:
        return _iterm_imgcat(path)
    elif os.environ.get("TERM_PROGRAM") == "WezTerm":
        return _wezterm_img(path)
    else:
        # 不支持图片的终端: 显示文件路径
        return False

def _kitty_icat(path: Path) -> bool:
    """Kitty 终端图片协议"""
    # Kitty 的 icat 命令
    result = subprocess.run(
        ["kitty", "+kitten", "icat", "--align", "left", str(path)],
        capture_output=True
    )
    return result.returncode == 0

def _iterm_imgcat(path: Path) -> bool:
    """iTerm2 内嵌图片协议"""
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    # iTerm2 的 OSC 1337 协议
    print(f"\033]1337;File=inline=1;size={len(data)}:{data}\a")
    return True

def _wezterm_img(path: Path) -> bool:
    """WezTerm 图片协议 (与 iTerm2 类似)"""
    return _iterm_imgcat(path)
```

**关于 imgcat**: 不需要外部依赖，使用 ANSI OSC 1337 转义序列即可。iTerm2 的 `imgcat` 脚本可以用纯 Python 实现。

#### 方案 B: ASCII/Unicode 字符画（全终端兼容）

对于简单图表（如柱状图、折线图），可以用 Unicode 字符近似绘制：

```
  y
  ↑
1.0 ┤         ╭────
0.8 ┤       ╭─╯
0.6 ┤     ╭─╯
0.4 ┤   ╭─╯
0.2 ┤ ╭─╯
0.0 ┼─╯────────────→ x
```

但这对于 matplotlib 生成的复杂图表不适用，仅作为降级方案。

#### 方案 C: 自动打开图片（简单实用）

```python
import webbrowser

def open_image(image_path: str):
    """用系统默认应用打开图片"""
    webbrowser.open(f"file://{Path(image_path).absolute()}")
```

### 3.3 推荐策略

**三级显示策略**，与数学公式类似：

```
优先级:
1. 支持图片协议的终端 → 内嵌显示 PNG
2. 不支持图片的终端 → 提示路径 + 询问是否用系统应用打开
3. Markdown 导出 → 自动嵌入 ![](path)
```

### 3.4 实现位置

在 `CLIUI.display_tool_result()` 中，检测到 `execute_python` 工具的结果包含 `images/` 路径时，自动尝试显示：

```python
# cli.py 中增强
def display_tool_result(self, tool_name: str, result: str):
    # 原有逻辑...
    super().display_tool_result(tool_name, result)

    # 如果是 Python 执行且结果包含图片路径
    if tool_name == "execute_python":
        import re
        images = re.findall(r'images/[^\s\'"]+\.(?:png|jpg|svg)', result)
        for img in images:
            if display_image_in_terminal(img):
                self.console.print(f"[dim]📊 图表已显示在上方[/]")
            else:
                self.console.print(f"[dim yellow]📊 图表已保存: {img}[/]")
                self.console.print(f"[dim]   (使用支持图片的终端可内嵌显示)[/]")
```

---

## 4. 其他改进建议

### 4.1 交互体验提升

#### A. 会话管理

```
# 新增 CLI 命令
history           — 显示最近会话列表
history <id>      — 回放指定会话
save              — 保存当前会话
export <format>   — 导出为 html / pdf / md
continue <id>     — 继续之前的会话
```

**实现**: 会话自动持久化到 `~/.math_assistant/sessions/`，使用 SQLite 索引。

#### B. 输入增强

| 特性 | 说明 | 依赖 |
|------|------|------|
| **多行输入** | `\` 结尾续行，或 `"""` 包裹多行 | 无 |
| **历史搜索** | `Ctrl+R` 搜索历史输入 | `readline` 或 `prompt_toolkit` |
| **自动补全** | LaTeX 命令补全、函数名补全 | `prompt_toolkit` |
| **语法高亮** | 输入中的代码块高亮 | `pygments` + `prompt_toolkit` |
| **快捷命令** | `!` 前缀执行 shell 命令 | 无 |

**推荐**: 将 `console.input()` 替换为 `prompt_toolkit` 的 `PromptSession`，获得完整的行编辑、历史、补全功能。

```python
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.styles import Style

class EnhancedCLIUI(CLIUI):
    def __init__(self):
        super().__init__()
        self.session = PromptSession(
            history=FileHistory(Path.home() / ".math_assistant" / "history"),
            auto_suggest=AutoSuggestFromHistory(),
            style=Style.from_dict({
                'prompt': 'ansigreen bold',
                '': 'ansicyan',
            }),
        )

    def get_user_input(self) -> str:
        return self.session.prompt([('class:prompt', '🧮 你: ')])
```

#### C. 进度与状态反馈

当前 `display_thinking()` 只显示 "Thinking..."，建议增强：

```python
def display_status(self, status: str, spinner: bool = True):
    """显示带 spinner 的状态信息"""
    from rich.live import Live
    from rich.spinner import Spinner
    ...
```

| 状态 | 显示 |
|------|------|
| 正在连接 API... | 🔄 Connecting... |
| 正在思考... | 🤔 Thinking... |
| 正在执行 Python 代码... | 🐍 Running Python... |
| 正在搜索... | 🔍 Searching web... |
| 正在生成图表... | 📊 Generating chart... |

#### D. 快捷键

```
Ctrl+C      — 中断当前操作（已支持）
Ctrl+D      — 退出
Ctrl+L      — 清屏
Ctrl+S      — 保存当前会话
Ctrl+R      — 搜索历史输入
Tab         — 自动补全
```

### 4.2 内容增强

#### A. 自动检测图表并展示

当前 agent 需要在代码中显式 `print('images/xxx.png')` 才能让系统知道生成了图表。改进方案：

```python
# python_executor.py 增强 — 自动检测生成的图片
def _collect_generated_images(image_dir: str, before_files: set) -> list[str]:
    """检测代码执行后新生成的图片文件"""
    after_files = set(Path(image_dir).glob("*.png"))
    new_files = after_files - before_files
    return [str(f) for f in new_files]
```

在 `execute_python` 工具执行前后对比 `images/` 目录，自动发现新生成的图片，无需 agent 手动 print。

#### B. 支持 SVG 图表

```python
# 在 python_executor.py 中同时支持 PNG 和 SVG
plt.savefig('images/chart.svg', format='svg', bbox_inches='tight')
```

SVG 在 Markdown 中兼容性好，且无限缩放不失真。

#### C. 数学步骤动画

对于分步求解过程，可生成多张图表展示每个步骤：

```python
# agent 自然支持：让模型多次调用 execute_python
for step in [1, 2, 3]:
    plt.figure()
    # 绘制第 step 步...
    plt.savefig(f'images/step_{step}.png')
```

在 Markdown 中表现为步骤序列，每步配一张图。

### 4.3 Markdown 导出增强

#### A. HTML 导出（带 MathJax）

```python
class HTMLExporter:
    """导出为独立 HTML 文件，内嵌 MathJax CDN"""

    TEMPLATE = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>{title}</title>
        <script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
        <style>
            body {{ font-family: system-ui; max-width: 800px; margin: 0 auto; padding: 2em; }}
            img {{ max-width: 100%; }}
            .tool-call {{ background: #f5f5f5; border-radius: 8px; padding: 1em; margin: 1em 0; }}
        </style>
    </head>
    <body>
        {content}
    </body>
    </html>
    """
```

#### B. PDF 导出

```python
# 使用 markdown + pandoc + tectonic/xelatex
# 或使用 weasyprint 直接从 HTML 转换
```

#### C. Typora/Notion 兼容

在 Markdown 中嵌入的图表使用相对路径 `./images/xxx.png`，导出时可选择：
- **保持相对路径**（适合版本管理）
- **Base64 内嵌**（单文件自包含）
- **复制到导出目录**（独立发布）

### 4.4 架构改进

#### A. 事件驱动架构

当前 `main.py` 中的 REPL 循环直接处理 LangGraph chunk，建议抽象为事件系统：

```python
from enum import Enum
from dataclasses import dataclass

class EventType(Enum):
    THINKING = "thinking"
    TEXT_DELTA = "text_delta"
    TOOL_CALL_START = "tool_call_start"
    TOOL_CALL_RESULT = "tool_call_result"
    IMAGE_GENERATED = "image_generated"
    ERROR = "error"
    FINISHED = "finished"

@dataclass
class AgentEvent:
    type: EventType
    data: dict
    timestamp: datetime
```

**好处**:
- UI 层和 SessionRecorder 可以独立订阅事件
- 易于添加新的输出目标（WebSocket、文件等）
- 便于测试

#### B. 工具插件化

```python
# 允许用户通过配置添加自定义工具
# config.yaml
tools:
  custom:
    - name: my_calculator
      module: my_tools.calculator
      class: MyCalculatorTool
```

#### C. 多模型支持

当前仅支持 DeepSeek（通过 OpenAI 兼容协议），可扩展：

```yaml
model:
  provider: openai  # openai | deepseek | anthropic | local
  name: gpt-4o
  base_url: https://api.openai.com/v1
```

### 4.5 用户体验优化

| 改进项 | 详情 |
|--------|------|
| **彩色 diff** | 代码修改前后对比用 diff 格式高亮 |
| **公式预览** | 输入公式时实时预览 Unicode 转换 |
| **例题推荐** | 会话结束时推荐相关例题 |
| **知识图谱** | 可视化展示已学概念之间的关系 |
| **难度自适应** | 根据用户水平调整解释的深度 |
| **语音输入** | 通过 Whisper API 语音转文字输入 |
| **暗色/亮色主题** | Rich 已支持，增加主题切换命令 |
| **通知提醒** | 长时间计算完成后桌面通知 |
| **多会话并行** | tmux/screen 式多会话管理 |

---

## 5. 实施优先级建议

### Phase 1: 快速见效（1-2 天）

```
🔴 P0 — 会话保存为 Markdown 文件
    ├── SessionRecorder + MarkdownExporter
    ├── 会话结束自动保存
    └── 图片自动嵌入 ![](path)

🔴 P0 — 基础数学公式优化
    ├── latex2unicode 转换
    ├── Rich 自定义 MathMarkdown 渲染
    └── SymPy pretty print 集成
```

### Phase 2: 体验提升（3-5 天）

```
🟡 P1 — prompt_toolkit 替换 console.input
    ├── 历史搜索 (Ctrl+R)
    ├── 自动补全
    └── 多行输入支持

🟡 P1 — 终端图片内嵌显示
    ├── iTerm2/Kitty 图片协议
    └── 自动检测终端能力

🟡 P1 — 会话管理
    ├── history 命令
    ├── SQLite 持久化
    └── 会话回放
```

### Phase 3: 长期优化（1-2 周）

```
🟢 P2 — HTML/PDF 导出
🟢 P2 — 事件驱动架构重构
🟢 P2 — SVG 图表支持
🟢 P2 — 工具插件化
🟢 P2 — 多模型支持
```

### Phase 4: 愿景功能（持续）

```
🔵 P3 — 语音输入输出
🔵 P3 — 知识图谱
🔵 P3 — 难度自适应
🔵 P3 — 协作白板
```

---

## 6. 输出格式选型分析

> 核心问题: 哪种文件格式最适合同时展示**图片图表**、**LaTeX 数学公式**和**超链接/交叉引用**？

### 6.1 候选格式对比

#### 对比总览

| 维度 | Markdown | HTML (自包含) | Jupyter `.ipynb` | PDF | Typst |
|------|----------|---------------|-------------------|-----|-------|
| **LaTeX 公式渲染** | ⭐⭐⭐ 依赖查看器 | ⭐⭐⭐⭐⭐ MathJax/KaTeX 完美 | ⭐⭐⭐⭐⭐ 原生 MathJax | ⭐⭐⭐⭐⭐ 原生 LaTeX 引擎 | ⭐⭐⭐⭐⭐ 原生数学排版 |
| **图片嵌入** | ⭐⭐⭐ 相对路径引用 | ⭐⭐⭐⭐⭐ base64 内嵌，自适应 | ⭐⭐⭐⭐⭐ 内嵌 base64 | ⭐⭐⭐⭐ 矢量嵌入 | ⭐⭐⭐⭐ 内嵌 |
| **超链接/交叉引用** | ⭐⭐ 基本链接，无交叉引用 | ⭐⭐⭐⭐⭐ 完整 HTML 链接体系 | ⭐⭐⭐ 支持 Markdown 链接 + anchor | ⭐⭐⭐⭐⭐ 完整 LaTeX 引用 | ⭐⭐⭐⭐⭐ 原生交叉引用 |
| **单文件自包含** | ⭐⭐ 图片需外带 | ⭐⭐⭐⭐⭐ 全部内嵌 | ⭐⭐⭐⭐⭐ 完全自包含 | ⭐⭐⭐⭐⭐ 完全自包含 | ⭐⭐⭐⭐⭐ 完全自包含 |
| **版本控制友好** | ⭐⭐⭐⭐⭐ 纯文本 diff | ⭐⭐ base64 膨胀 diff | ⭐ json 格式可 diff | 二进制不可 diff | ⭐⭐⭐ 纯文本 |
| **生成复杂度** | ⭐⭐⭐⭐⭐ 极简 | ⭐⭐⭐ 需模板引擎 | ⭐⭐⭐ 需 nbformat | ⭐ 需 LaTeX 发行版 | ⭐ 需 Typst 编译器 |
| **文件体积** | ⭐⭐⭐⭐⭐ ~5KB | ⭐⭐⭐ ~200KB (含图) | ⭐⭐⭐ ~200KB | ⭐⭐⭐⭐ ~100KB | ⭐⭐⭐⭐ ~100KB |
| **跨平台查看** | ⭐⭐⭐⭐ 任何编辑器 | ⭐⭐⭐⭐⭐ 浏览器即开 | ⭐⭐ 需 Jupyter 环境 | ⭐⭐⭐⭐⭐ 任何 PDF 阅读器 | ⭐⭐ 需 Typst 工具 |
| **可扩展性** | ⭐⭐ 受限于 Markdown 语法 | ⭐⭐⭐⭐⭐ 可嵌入 Plotly/D3/音频等 | ⭐⭐⭐⭐⭐ 可交互执行代码 | ⭐ 静态不可扩展 | ⭐⭐⭐ 有限扩展 |
| **依赖** | 零依赖 | 零依赖（自包含） | JupyterLab/VS Code | PDF 阅读器 | Typst CLI |

#### 各格式详细分析

**1. Markdown (`.md`)**

```markdown
优点:
✅ 纯文本，git diff 友好，适合版本管理
✅ VS Code / GitHub / Typora 原生支持 MathJax 渲染 LaTeX（预览时）
✅ 生成极简 — 只需字符串拼接
✅ 生态最大，工具链最成熟

缺点:
❌ LaTeX 渲染依赖查看器，纯文本下只能看源码
❌ 图片只能是相对路径引用，无法内嵌（分享时需打包整个目录）
❌ 无交叉引用系统（不能 "见公式 (3)" 自动跳转）
❌ 无原生 callout/admonition（用 > blockquote 模拟）
❌ 未来加交互式图表(Plotly) / 动画时完全无能为力

适合场景: 源码级存储 + Git 版本管理
```

**2. 自包含 HTML (`.html`)** ⭐ 推荐首选导出格式

```html
优点:
✅ MathJax 或 KaTeX 完美渲染所有 LaTeX，包括 \begin{align} 等复杂环境
✅ 图片 base64 内嵌，单文件即开即用，任何浏览器打开
✅ 完整超链接体系：锚点跳转、外部链接、脚注、引用
✅ 可嵌入 Plotly 交互图表、GeoGebra、3D 图形、音频/视频
✅ 响应式布局，手机/平板/桌面都能看
✅ CSS 打印样式 → 可直接打印为 PDF
✅ 零依赖：一个 .html 文件，微信/邮件发送即看
✅ 未来可嵌入：动画、代码运行器、问答互动组件

缺点:
❌ 文件体积较大（base64 图片使体积膨胀 ~33%）
❌ git diff 不友好（base64 块污染 diff）
❌ 生成需要模板引擎（Jinja2）

适合场景: 分享/发布/归档的最佳格式
```

**3. Jupyter Notebook (`.ipynb`)**

```json
优点:
✅ 数学 + 代码 + 图表 + 文字天然一体
✅ 原生 MathJax，公式渲染完美
✅ 图片内嵌 base64
✅ 代码块可重新执行（交互式学习！）
✅ VS Code 原生支持，无需安装 Jupyter
✅ 可导出为 HTML/PDF/Markdown/Reveal.js 幻灯片

缺点:
❌ JSON 格式，裸看不可读
❌ 必须用 VS Code / JupyterLab 打开
❌ 分享不如 HTML 方便（对方也需要相应环境）
❌ 版本控制体验一般（JSON diff，虽可配 jupytext）

适合场景: 交互式数学学习笔记，用户想自己改代码跑跑看
```

**4. PDF (`.pdf`)**

```latex
优点:
✅ 终极排版质量，专业论文级别
✅ 任何设备都能打开，最通用格式
✅ 可打印

缺点:
❌ 生成需要 LaTeX 发行版（~2GB）或 Typst
❌ 静态不可交互
❌ 对代码块/长文本排版需仔细处理
❌ 生成流程复杂（.md → .tex → .pdf 或多工具链）

适合场景: 需要打印的正式文档
```

**5. Typst (`.typ`)**

```
优点:
✅ 新一代排版语言，比 LaTeX 简洁 10 倍
✅ 编译极快（毫秒级），单一 ~40MB 二进制
✅ 原生数学排版媲美 LaTeX
✅ 可编程生成（函数、循环、条件）
✅ 输出 PDF/PNG/SVG

缺点:
❌ 生态不如 LaTeX 成熟
❌ 查看需编译为 PDF
❌ 不是"所见即所得"的分享格式

适合场景: 自动批量生成排版精美的数学文档
```

### 6.2 推荐方案: 多格式分层策略

```
┌─────────────────────────────────────────────────┐
│                 MathAssistant 输出体系             │
├─────────────────────────────────────────────────┤
│                                                   │
│  第 1 层: Markdown (存储层)                       │
│  ├── 轻量纯文本，git 版本管理                      │
│  ├── YAML frontmatter 元数据                      │
│  ├── 图片用相对路径引用 (images/*.png)             │
│  ├── LaTeX 保持 $...$ 源码                        │
│  └── 会话结束后自动保存到 sessions/                │
│                                                   │
│  第 2 层: HTML 自包含 (发布层) ⭐ 核心              │
│  ├── 单文件 .html，任何浏览器打开                   │
│  ├── 内嵌 MathJax CDN (或本地 bundle)              │
│  ├── 图片全部 base64 内嵌                          │
│  ├── 完整超链接/脚注/交叉引用                       │
│  ├── 响应式布局 + 暗色/亮色主题                     │
│  ├── 可一键打印为 PDF                               │
│  └── 未来扩展: Plotly 交互图 / 代码运行器            │
│                                                   │
│  第 3 层: Jupyter Notebook (交互层，未来)           │
│  ├── 用户可重新执行代码                             │
│  ├── 修改参数看不同结果                             │
│  └── 适合"动手学习"场景                             │
│                                                   │
└─────────────────────────────────────────────────┘
```

### 6.3 HTML 自包含文件示例

用来说明 "自包含 HTML 到底长什么样"：

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>求解 x² - 5x + 6 = 0 — MathAssistant</title>
<!-- KaTeX: 零外部依赖的轻量级 LaTeX 渲染 (~280KB) -->
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16/dist/katex.min.css">
<script src="https://cdn.jsdelivr.net/npm/katex@0.16/dist/katex.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/katex@0.16/dist/contrib/auto-render.min.js"></script>
<style>
  :root {
    --bg: #fff; --text: #1a1a1a; --code-bg: #f5f5f5;
    --border: #e0e0e0; --accent: #2563eb;
  }
  @media (prefers-color-scheme: dark) {
    :root { --bg: #1a1a2e; --text: #e0e0e0; --code-bg: #2a2a3e; }
  }
  body {
    font-family: system-ui, -apple-system, sans-serif;
    max-width: 800px; margin: 0 auto; padding: 2em;
    background: var(--bg); color: var(--text); line-height: 1.7;
  }
  img { max-width: 100%; border-radius: 8px; border: 1px solid var(--border); }
  .tool-call { background: var(--code-bg); border-radius: 8px; padding: 1em; margin: 1em 0; }
  .tool-call summary { cursor: pointer; color: var(--accent); font-weight: bold; }
  table { border-collapse: collapse; width: 100%; }
  th, td { border: 1px solid var(--border); padding: 8px; text-align: left; }
  a { color: var(--accent); }
  /* 打印样式：自动去掉背景色 */
  @media print { body { background: white; color: black; } }
</style>
</head>
<body>

<h1>🧮 求解 x² - 5x + 6 = 0</h1>

<p><strong>会话 ID</strong>: <code>a1b2c3d4</code> ·
   <strong>日期</strong>: 2026-06-24 ·
   <strong>模型</strong>: deepseek-chat</p>

<p>二次方程 \(x^2 - 5x + 6 = 0\) 可通过因式分解求解：</p>

\[
x^2 - 5x + 6 = (x-2)(x-3) = 0
\]

<p>因此 <b>解为 \(x = 2\) 或 \(x = 3\)</b>。</p>

<details class="tool-call">
  <summary>🔧 execute_python — 验证结果</summary>
  <pre><code>import sympy as sp
x = sp.symbols('x')
sol = sp.solve(x**2 - 5*x + 6, x)
print(sol)  # [2, 3]</code></pre>
  <p><b>输出:</b> [2, 3]</p>
</details>

<h3>📊 图表</h3>
<img src="data:image/png;base64,iVBORw0KGgo..." alt="二次函数图像">
<p><em>图: y = x² - 5x + 6 的图像，零点在 x=2 和 x=3</em></p>

<h3>🔗 相关链接</h3>
<ul>
  <li><a href="#q2">Q2: 求该二次函数的顶点坐标</a></li>
  <li><a href="https://en.wikipedia.org/wiki/Quadratic_equation" target="_blank">
    维基百科: 二次方程</a></li>
  <li><a href="https://www.desmos.com/calculator" target="_blank">
    Desmos 在线作图验证</a></li>
</ul>

<script>
  // 自动渲染页面中所有 LaTeX 公式
  renderMathInElement(document.body, {
    delimiters: [
      {left: '$$', right: '$$', display: true},
      {left: '$', right: '$', display: false},
      {left: '\\(', right: '\\)', display: false},
      {left: '\\[', right: '\\]', display: true},
    ]
  });
</script>
</body>
</html>
```

### 6.4 KaTeX vs MathJax 选择

| | KaTeX | MathJax |
|------|-------|---------|
| **速度** | ⚡ 极快（毫秒级渲染） | 🐢 较慢（秒级） |
| **体积** | ~280KB | ~2MB（完整版） |
| **LaTeX 支持** | 覆盖 90% 常用语法 | 覆盖几乎所有 LaTeX 包 |
| **适用场景** | 内嵌 HTML，快速渲染 | 学术论文级复杂公式 |
| **CDN** | jsdelivr | jsdelivr / unpkg |

**推荐**: 默认使用 **KaTeX**（轻量快速，对数学教学场景足够）。当检测到不支持的 LaTeX 命令时，自动切换 MathJax。

### 6.5 图片内嵌策略

```python
# 三种模式可配置

class ImageMode(Enum):
    RELATIVE = "relative"   # Markdown 原样: ![](images/foo.png)
    BASE64 = "base64"       # HTML 内嵌: <img src="data:image/png;base64,...">
    EXTERNAL = "external"   # 复制到输出目录: <img src="./foo.png">

# 推荐默认值
# .md 导出 → RELATIVE (保持 git 友好)
# .html 导出 → BASE64 (单文件自包含)
```

### 6.6 最终结论

```
┌──────────────────────────────────────────────────────┐
│                                                      │
│   存储格式:  Markdown (.md)    ← git 版本管理        │
│   发布格式:  自包含 HTML       ← 分享 / 查看 / 打印   │
│   交互格式:  Jupyter (.ipynb)  ← 边学边改代码 (未来)  │
│   打印格式:  浏览器 Ctrl+P     ← 无需单独 PDF 生成    │
│                                                      │
│   HTML 自包含是最核心的产出格式，因为：                │
│   1. LaTeX → KaTeX 完美渲染                           │
│   2. 图片 → base64 全部内嵌                           │
│   3. 链接 → 完整 HTML 超链接 + 交叉引用                │
│   4. 零依赖 → 一个文件，浏览器即开                     │
│   5. 可扩展 → 未来加交互图表/动画/代码运行器           │
│                                                      │
└──────────────────────────────────────────────────────┘
```

---

## 附录: 依赖清单

```toml
# 新增依赖 (pyproject.toml)
[project]
dependencies = [
    # 现有依赖...
    "langchain>=1.0",
    "langchain-openai>=1.0",
    "sympy>=1.12",
    "numpy>=1.26",
    "matplotlib>=3.8",
    "duckduckgo-search>=7.0",
    "pyyaml>=6.0",
    "rich>=13.0",
    "pydantic>=2.0",

    # Phase 1 新增
    "latex2unicode>=0.1.0",       # LaTeX → Unicode (纯 Python, ~50KB)
    "python-frontmatter>=1.0",    # Markdown frontmatter 解析

    # Phase 2 新增
    "prompt-toolkit>=3.0",        # 增强终端输入 (历史、补全)
    "term-image>=0.7.0",         # 终端图片显示 (可选)

    # Phase 3 新增
    "jinja2>=3.0",                # HTML/PDF 模板引擎
    # "weasyprint>=60.0",         # HTML → PDF (可选, 较重)
]
```

---

> **总结**: 核心改进路径清晰——先让内容可保存、可回溯（MD 导出），再让终端内的数学公式更好看（Unicode + 颜色），然后让图表在能力范围内尽量直接显示。这三个改进能立刻让 MathAssistant 从"命令行工具"进化为"数学学习助手"。
