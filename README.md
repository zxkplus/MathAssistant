# 🧮 MathAssistant — AI-Powered Mathematics Teacher

MathAssistant 是一个由大语言模型驱动的智能数学教学系统，包含 **CLI 交互式学习助手** 和 **后端用户管理系统** 两个核心组件。它能够解答数学问题、绘制函数图表、自动标注知识点，并追踪每位学习者的学力成长轨迹。

---

## 目录

- [核心特性](#核心特性)
- [系统架构](#系统架构)
- [快速开始](#快速开始)
- [配置说明](#配置说明)
- [CLI 交互式助手](#cli-交互式助手)
  - [基础用法](#基础用法)
  - [REPL 命令](#repl-命令)
  - [工具说明](#工具说明)
- [用户管理后端](#用户管理后端)
  - [启动服务](#启动服务)
  - [知识体系导航](#知识体系导航)
  - [自动标注与学力追踪](#自动标注与学力追踪)
  - [API 概览](#api-概览)
- [项目结构](#项目结构)
- [学力分析引擎](#学力分析引擎)
- [开发指南](#开发指南)
- [License](#license)

---

## 核心特性

### 🎓 CLI 智能数学导师

- **自然语言交互**：用中文或英文描述任何数学问题，AI 会逐步讲解推理过程
- **符号计算**：通过 SymPy 求解方程、求导、积分、极限、矩阵运算等
- **数值计算**：利用 NumPy 进行数值分析和统计
- **图表生成**：通过 Matplotlib 生成函数图像，支持终端内嵌显示（Kitty / iTerm2）
- **联网搜索**：自动检索数学定理、定义和历史背景
- **会话记录**：自动导出 Markdown 或自包含 HTML（支持 KaTeX 数学公式渲染）
- **多轮对话**：基于 LangGraph 的状态图维护上下文记忆

### 📊 用户管理后端 (FastAPI)

- **账户系统**：注册 / 登录 / JWT 认证
- **知识体系**：70+ 个数学知识点，三层树形结构，从算术到离散数学
- **智能标注**：LLM 自动分析问题涉及的知识点，支持手动修正
- **掌握度评分**：加权算法（近期表现 50% + 长期正确率 30% + 连续正确奖励 20%）
- **薄弱项检测**：综合得分 × 尝试次数 × 近期错误加权的弱点排名
- **错题本**：错误类型分类（概念错误 / 计算错误 / 审题不清 / 粗心 / 未知）
- **学习推荐**：基于前置知识和薄弱点的个性化学习路径建议
- **趋势分析**：按周/月统计提问频率、正确率、新知识点探索

---

## 系统架构

```
┌──────────────────────────────────────────────────────────┐
│                      用户界面层                           │
│  ┌─────────────────────┐    ┌────────────────────────┐   │
│  │   CLI (Rich/TUI)    │    │   Swagger UI / HTTP    │   │
│  │   main.py REPL      │    │   /docs (FastAPI)      │   │
│  └────────┬────────────┘    └───────────┬────────────┘   │
│           │                             │                 │
├───────────┼─────────────────────────────┼─────────────────┤
│           │        核心逻辑层            │                 │
│  ┌────────▼────────┐   ┌───────────────▼─────────────┐   │
│  │  LangGraph Agent │   │  FastAPI Routers            │   │
│  │  - System Prompt │   │  - Auth / Questions / KPs   │   │
│  │  - 2 Tools       │   │  - Analytics / Tags         │   │
│  │  - Middleware     │   │                             │   │
│  │  - MemorySaver    │   │  Services:                  │   │
│  └────────┬────────┘   │  - TaggingService (LLM)      │   │
│           │             │  - AnalyticsEngine            │   │
│           │             │  - AuthService (bcrypt+JWT)  │   │
│           │             └───────────────┬─────────────┘   │
├───────────┼─────────────────────────────┼─────────────────┤
│           │        数据与工具层          │                 │
│  ┌────────▼────────┐   ┌───────────────▼─────────────┐   │
│  │  Tools           │   │  SQLAlchemy ORM             │   │
│  │  - execute_python│   │  - SQLite (单文件)           │   │
│  │  - web_search    │   │  - 7 Models                 │   │
│  └────────┬────────┘   └───────────────┬─────────────┘   │
│           │                             │                 │
│  ┌────────▼────────┐                   │                 │
│  │  DeepSeek API    │                   │                 │
│  │  (OpenAI-compat) │                   │                 │
│  └─────────────────┘                   │                 │
└──────────────────────────────────────────────────────────┘
```

**数据流概要**：

1. 用户输入 → `main.py` 解析命令 → 如果是数学问题则提交给 Agent
2. Agent (LangGraph) 调用 LLM (DeepSeek)，LLM 可决定调用工具（Python 执行 / 网络搜索）
3. 工具结果返回 LLM，生成最终回答
4. 会话记录器 (`SessionRecorder`) 累积问答 → 导出为 Markdown / HTML
5. （可选）CLI 通过 `cli_client.py` 将问题提交给后端 → 后端触发 LLM 自动标注 → 用户反馈正确/错误 → 掌握度更新

---

## 快速开始

### 前置条件

- Python ≥ 3.11
- DeepSeek API Key（[获取地址](https://platform.deepseek.com/)）或 OpenAI API Key

### 安装

```bash
# 克隆仓库
git clone <repo-url>
cd MathAssistant

# 基础安装（仅 CLI）
pip install -e .

# 带终端数学公式渲染增强
pip install -e ".[math-render]"

# 带后端服务（用户管理 + 学力分析）
pip install -e ".[server]"

# 全部安装
pip install -e ".[math-render,server]"
```

### 配置 API Key

创建 `config.local.yaml`（已被 .gitignore 忽略）：

```yaml
api:
  api_key: "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

或通过环境变量设置：

```bash
export DEEPSEEK_API_KEY="sk-xxx"
```

### 启动 CLI

```bash
# 基础启动
python -m math_assistant.main

# 指定模型
python -m math_assistant.main --model deepseek-chat

# 连接后端以获得学力追踪
python -m math_assistant.main --backend-url http://127.0.0.1:8000 --backend-user alice
```

### 启动后端

```bash
# 默认 127.0.0.1:8000
python -m math_assistant.server.main

# 打开 Swagger 交互文档
open http://127.0.0.1:8000/docs
```

---

## 配置说明

MathAssistant 使用三层配置加载机制（高优先级覆盖低优先级）：

| 优先级 | 来源 | 用途 |
|--------|------|------|
| 1（最低） | `config.yaml` | 项目级默认配置（可提交到 git） |
| 2 | `config.local.yaml` | 本地私密配置（API Key，已 gitignore） |
| 3（最高） | 环境变量 | 运行时覆盖（`MATH_ASSISTANT_*` 前缀） |

### config.yaml 参考

```yaml
model:
  provider: deepseek          # LLM 提供商
  name: deepseek-chat         # 模型名称
  temperature: 0.0            # 温度（0.0 ~ 2.0，推荐 0.0 以获得确定性回答）

api:
  base_url: "https://api.deepseek.com"

search:
  provider: duckduckgo        # 搜索后端（可插拔，目前仅支持 duckduckgo）

python_executor:
  timeout_seconds: 30         # Python 代码执行超时（1 ~ 120 秒）

agent:
  max_tool_calls: 20          # 每轮最多工具调用次数（1 ~ 100）

output:
  image_dir: "./images"       # 图表保存目录
  save_mode: "session"        # 保存模式：session（退出时）/ turn（逐轮）/ manual（手动）
  save_dir: "./sessions"      # 会话导出目录
  html_export: true           # 是否同时导出自包含 HTML
  embed_images: true          # HTML 中内嵌 base64 图片
```

### server.yaml 参考

```yaml
host: "127.0.0.1"
port: 8000
database:
  url: "sqlite:///./math_assistant.db"
auth:
  secret_key: "your-random-secret-here"     # 生产环境务必修改
  algorithm: "HS256"
  access_token_expire_minutes: 1440          # Token 有效期（24 小时）
```

---

## CLI 交互式助手

### 基础用法

```
=================================================================
  🧮  MathAssistant — Your AI Mathematics Teacher
=================================================================

I'm ready to help you with any math problem! Try asking me:
  • "Solve x² - 5x + 6 = 0"
  • "Explain what a derivative is and plot y = sin(x)"
  • "What is the Fundamental Theorem of Calculus?"
  • "Find the eigenvalues of [[1,2],[3,4]]"
  • "Calculate the probability of rolling a sum of 7 with two dice"

Type 'quit' or 'exit' to leave.
=================================================================

>>> 用中文解释一下什么是拉格朗日中值定理
```

> 💡 **提示**：系统提示词设置为 "优先使用中文回答"，所以你可以直接用中文提问。

### REPL 命令

| 命令 | 说明 |
|------|------|
| `:quit` / `exit` / `q` | 退出程序（自动保存会话） |
| `:new` / `reset` | 开始新对话（自动保存当前会话） |
| `:save` / `:export` | 手动导出当前会话 |
| `:save md` | 仅导出 Markdown |
| `:save html` | 仅导出自包含 HTML |
| `:help` | 显示帮助信息 |
| `:correct` / `:c` | ⚡ 标记上一题为正确（需连接后端） |
| `:wrong` / `:w` | ⚡ 标记上一题为错误（需连接后端） |
| `:stats` | ⚡ 显示学力概览（需连接后端） |
| `:mistakes` | ⚡ 显示最近错题（需连接后端） |
| `:recommend` | ⚡ 显示学习推荐（需连接后端） |

### 工具说明

#### `execute_python` — Python 代码执行

Agent 会在需要计算、求解或绘图时自动生成并执行 Python 代码。

**可用库**：`sympy`、`numpy`、`matplotlib`、`math`、`json`、`fractions`、`decimal`、`itertools`、`collections`、`random`

**安全机制**：
- 子进程隔离执行
- 可配置超时（默认 30 秒）
- 临时文件自动清理
- Matplotlib Agg 后端（无 GUI 依赖）

#### `web_search` — 网络搜索

Agent 自动通过 DuckDuckGo 搜索数学定理、定义或参考资料。搜索结果会标注来源 URL。

**可插拔架构**：通过继承 `BaseSearchProvider` 并注册到 `PROVIDER_REGISTRY` 即可添加新的搜索后端。

---

## 用户管理后端

后端是一个独立的 FastAPI 服务，提供完整的用户管理、知识体系维护、智能题目标注和学力分析功能。

### 启动服务

```bash
# 安装依赖
pip install -e ".[server]"

# 启动服务（默认 127.0.0.1:8000）
python -m math_assistant.server.main

# 首次启动后，初始化数学知识体系
curl -X POST http://127.0.0.1:8000/api/knowledge-points/seed

# 注册用户
curl -X POST http://127.0.0.1:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","email":"alice@example.com","password":"password123"}'

# 登录获取 Token
curl -X POST http://127.0.0.1:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"password123"}'
```

### 知识体系导航

系统内置了一个包含 **72 个知识点、9 大类别** 的数学知识体系：

```
Math
├── Arithmetic (算术)
│   ├── Basic Operations
│   ├── Fractions and Decimals
│   ├── Percentages
│   ├── Factors and Multiples
│   └── Exponents and Roots
├── Algebra (代数)
│   ├── Linear Equations
│   ├── Quadratic Equations
│   ├── Polynomials
│   ├── Inequalities
│   ├── Systems of Equations
│   ├── Functions and Graphs
│   ├── Exponents and Logarithms
│   ├── Rational Expressions
│   ├── Sequences and Series
│   └── Complex Numbers
├── Geometry (几何)
│   ├── Lines and Angles
│   ├── Triangles
│   ├── Circles
│   ├── Polygons
│   ├── Area and Perimeter
│   ├── Volume and Surface Area
│   ├── Coordinate Geometry
│   ├── Transformations
│   └── Geometric Proofs
├── Trigonometry (三角学)
│   ├── Sine, Cosine, Tangent
│   ├── Unit Circle
│   ├── Trigonometric Identities
│   ├── Trigonometric Equations
│   ├── Law of Sines and Cosines
│   └── Graphs of Trig Functions
├── Calculus (微积分)
│   ├── Limits and Continuity
│   ├── Derivatives
│   ├── Derivative Rules
│   ├── Applications of Derivatives
│   ├── Integrals
│   ├── Integration Techniques
│   ├── Applications of Integrals
│   ├── Differential Equations
│   ├── Multivariable Calculus
│   └── Sequences and Series (Calc)
├── Probability and Statistics (概率与统计)
│   ├── Counting Principles
│   ├── Probability Rules
│   ├── Random Variables
│   ├── Statistical Measures
│   ├── Distributions
│   ├── Hypothesis Testing
│   ├── Regression and Correlation
│   └── Data Visualization
├── Linear Algebra (线性代数)
│   ├── Vectors
│   ├── Matrices
│   ├── Determinants
│   ├── Eigenvalues and Eigenvectors
│   ├── Linear Transformations
│   └── Systems of Linear Equations
├── Number Theory (数论)
│   ├── Prime Numbers
│   ├── Divisibility
│   ├── Modular Arithmetic
│   └── Diophantine Equations
└── Discrete Mathematics (离散数学)
    ├── Logic and Proofs
    ├── Set Theory
    ├── Combinatorics
    ├── Graph Theory
    └── Recurrence Relations
```

### 自动标注与学力追踪

**问题标注流程**：

1. 用户提交问题 → `POST /api/questions`
2. 后台异步触发 LLM 分析 → 将问题映射到知识体系
3. LLM 返回候选知识点 → 与数据库中的知识体系进行模糊匹配（防止幻觉）
4. 自动创建标签（`source=auto`, confidence=LLM 输出的置信度）
5. 用户可通过 `PUT /api/questions/{id}/tags` 手动修正标签（`source=manual`, confidence=1.0, `is_user_corrected=True`）

**学力追踪流程**：

1. 用户提交问题答案 → `POST /api/questions/{id}/answer`（`is_correct` + `mistake_type`）
2. 自动触发掌握度重算 → `update_mastery_score()`
3. 分析引擎检测薄弱点 → 生成个性化学习推荐

### API 概览

完整的 API 文档可通过启动后端后访问：

```
http://127.0.0.1:8000/docs    # Swagger UI（交互式）
http://127.0.0.1:8000/redoc   # ReDoc（只读）
```

#### 认证 `/api/auth`

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/register` | 注册新用户 |
| POST | `/login` | 登录获取 JWT Token |
| GET | `/me` | 获取当前用户信息 |
| PUT | `/me` | 更新个人资料 |
| PUT | `/me/password` | 修改密码 |

#### 知识体系 `/api/knowledge-points`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 列出知识点（支持按 parent_id / search / depth 过滤） |
| GET | `/tree` | 获取完整树形层级结构 |
| GET | `/{id}` | 获取单个知识点详情 |
| GET | `/{id}/children` | 获取直接子节点 |
| POST | `/` | 创建新知识点 |
| POST | `/seed` | 一键初始化默认知识体系（幂等） |

#### 题目 `/api/questions`

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/` | 提交问题（异步触发 LLM 自动标注） |
| GET | `/` | 问题列表（分页 + 多维度筛选） |
| GET | `/{id}` | 获取问题详情（含标签和答案记录） |
| PUT | `/{id}` | 更新问题内容 |
| PUT | `/{id}/tags` | **手动修正标签**（覆盖自动标注） |
| DELETE | `/{id}` | 删除问题（级联删除标签和答案） |
| POST | `/{id}/answer` | 记录答案结果（触发掌握度更新） |

#### 学力分析 `/api/analytics`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/mastery` | 全知识点掌握度概览 |
| GET | `/mastery/{kp_id}` | 单个知识点的详细掌握历史 |
| GET | `/trends` | 学习趋势（按周/月统计） |
| GET | `/weaknesses` | 薄弱项排名 |
| GET | `/recommendations` | 学习路径推荐 |
| GET | `/mistake-notebook` | 错题本（分页 + 按类型筛选） |
| GET | `/summary` | 学习概览（总分 / 最强 / 最弱 / 连续天数） |

---

## 项目结构

```
MathAssistant/
├── config.yaml                  # 主配置文件（可提交）
├── config.local.yaml            # 本地密钥配置（gitignore）
├── server.yaml                  # 后端服务配置
├── pyproject.toml               # 项目元数据 + 依赖
├── run.py                       # 便捷启动脚本（Windows UTF-8 修复）
├── images/                      # 生成的图表保存目录
├── sessions/                    # 会话导出目录
│
└── src/math_assistant/
    ├── __init__.py
    ├── main.py                  # CLI 入口 + REPL 循环
    ├── agent.py                 # Agent 组装（LLM + 工具 + 中间件 + 记忆）
    ├── config.py                # 配置模型（Pydantic + 三层加载）
    ├── prompts.py               # 系统提示词 + 欢迎消息
    │
    ├── tools/                   # Agent 工具
    │   ├── python_executor.py   # Python 代码隔离执行
    │   └── search.py            # 网络搜索工具
    │
    ├── search_providers/        # 搜索后端（可插拔）
    │   ├── base.py              # BaseSearchProvider 抽象类
    │   └── duckduckgo.py        # DuckDuckGo 实现
    │
    ├── ui/                      # 用户界面层
    │   ├── base.py              # AbstractUI 抽象类
    │   ├── cli.py               # Rich 终端 UI 实现
    │   └── renderer.py          # 数学公式 Unicode 渲染
    │
    ├── session/                 # 会话录制与导出
    │   ├── recorder.py          # Session / Turn / ToolCallRecord 数据模型
    │   └── exporter.py          # Markdown + HTML 导出器（支持 KaTeX）
    │
    └── server/                  # 🔥 后端服务（用户管理 + 学力分析）
        ├── __init__.py
        ├── main.py              # FastAPI 应用工厂 + uvicorn 入口
        ├── config.py            # ServerConfig 配置模型
        ├── database.py          # SQLAlchemy 引擎 + Session + Base
        ├── dependencies.py      # FastAPI 依赖注入（get_db / get_current_user）
        ├── cli_client.py        # CLI ↔ 后端 HTTP 客户端
        │
        ├── models/              # ORM 数据模型（7 张表）
        │   ├── user.py          # User — 用户账户
        │   ├── knowledge_point.py # KnowledgePoint — 知识点（自引用树）
        │   ├── question.py      # Question — 用户提问
        │   ├── question_tag.py  # QuestionTag — 问题标签（auto/manual）
        │   ├── answer_record.py # AnswerRecord — 答案记录（错题本）
        │   ├── mastery.py       # MasteryScore — 预计算掌握度
        │   └── learning_session.py # LearningSession — 学习会话
        │
        ├── schemas/             # Pydantic 请求/响应模型
        │   ├── auth.py          # 认证相关
        │   ├── knowledge_point.py # 知识点相关
        │   ├── question.py      # 问题相关
        │   └── analytics.py     # 分析相关
        │
        ├── routers/             # API 路由
        │   ├── auth.py          # /api/auth/*
        │   ├── knowledge_points.py # /api/knowledge-points/*
        │   ├── questions.py     # /api/questions/*
        │   └── analytics.py     # /api/analytics/*
        │
        └── services/            # 业务逻辑层
            ├── auth_service.py  # bcrypt 密码哈希 + JWT 令牌
            ├── tagging_service.py # LLM 自动标注（复用 DeepSeek 配置）
            ├── analytics_engine.py # 掌握度 / 趋势 / 薄弱项 / 推荐算法
            └── taxonomy_seed.py # 72 个条目的默认知识体系
```

---

## 学力分析引擎

### 掌握度评分算法

每个（用户, 知识点）的掌握度分数（0–100）由三部分加权计算：

```
近期准确率 (recent_accuracy)  = 近30天正确数 / max(近30天尝试数, 1)
长期准确率 (overall_accuracy)  = 总正确数 / max(总尝试数, 1)
连续正确因子 (streak_factor)   = min(连续正确次数 / 10, 1.0)

掌握度分数 = 0.5 × recent_accuracy × 100
           + 0.3 × overall_accuracy × 100
           + 0.2 × streak_factor × 100

置信度 = min(总尝试次数 / 20, 1.0)   # 需要约 20 次尝试才能达到完全置信
```

**设计理念**：
- **近期优先**（50% 权重）：最近的表现最能反映当前掌握水平
- **长期一致**（30% 权重）：持续的正确率比偶然正确更有意义
- **连续奖励**（20% 权重）：连续 10 次正确 = 满分奖励，激励持续努力的势头

### 薄弱项检测

```
薄弱分数 = (100 - 掌握度) × ln(尝试次数 + 1) × 近期惩罚

近期惩罚 = 1.5（过去 7 天有错误）或 1.0
```

薄弱项按薄弱分数降序排列，优先暴露那些 "一直在尝试但持续出错" 的知识点。

### 学习推荐

1. 筛选确认的薄弱点（得分 < 50，置信度 > 0.3，至少 3 次尝试）
2. 检查前置依赖 —— 如果前置知识点也薄弱，优先推荐复习前置知识
3. 按 `薄弱分数 × 知识点重要度` 排序
4. 根据掌握度水平分配行动类型：

| 掌握度 | 行动类型 | 说明 |
|--------|----------|------|
| < 30, 尝试 < 5 | `review_concept` | 先学习概念基础 |
| 30–60 | `practice_problems` | 针对性刷题 |
| 前置薄弱 | `prerequisite_review` | 先补前置知识 |
| ≥ 70 | `advanced_challenge` | 挑战更高阶的内容 |

---

## 开发指南

### 添加新的搜索后端

1. 继承 `src/math_assistant/search_providers/base.py` 中的 `BaseSearchProvider`
2. 实现 `search(query, max_results)` 和 `name()` 方法
3. 在 `src/math_assistant/search_providers/__init__.py` 的 `PROVIDER_REGISTRY` 中注册
4. 在 `config.yaml` 中设置 `search.provider` 为你注册的名称

### 添加新的 UI 前端

1. 继承 `src/math_assistant/ui/base.py` 中的 `AbstractUI`
2. 实现全部 9 个抽象方法
3. 在 `main.py` 中将 `CLIUI()` 替换为你的实现

### 添加新的知识体系类别

编辑 `src/math_assistant/server/services/taxonomy_seed.py` 中的 `TAXONOMY` 字典，或通过 API 动态添加：

```bash
curl -X POST http://127.0.0.1:8000/api/knowledge-points \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name":"New Topic","parent_id":null,"description":"Description","importance":0.8}'
```

### 自定义掌握度算法

编辑 `src/math_assistant/server/services/analytics_engine.py` 中顶部的权重常量：

```python
RECENCY_WEIGHT = 0.5         # 调整近期权重
CONSISTENCY_WEIGHT = 0.3     # 调整长期权重
STREAK_BONUS = 0.2           # 调整连续正确奖励
STREAK_CAP = 10              # 调整连续正确上限
CONFIDENCE_THRESHOLD = 20    # 调整置信度阈值
```

### 环境变量覆盖

所有配置项都可通过环境变量覆盖（最高优先级）：

| 环境变量 | 对应配置 |
|----------|----------|
| `MATH_ASSISTANT_API_KEY` | `api.api_key` |
| `DEEPSEEK_API_KEY` | `api.api_key` |
| `OPENAI_API_KEY` | `api.api_key` |
| `MATH_ASSISTANT_MODEL` | `model.name` |
| `MATH_ASSISTANT_TEMPERATURE` | `model.temperature` |
| `MATH_ASSISTANT_SEARCH_PROVIDER` | `search.provider` |
| `MATH_ASSISTANT_PYTHON_TIMEOUT` | `python_executor.timeout_seconds` |
| `MATH_ASSISTANT_MAX_TOOL_CALLS` | `agent.max_tool_calls` |
| `MATH_ASSISTANT_SERVER_PORT` | 后端服务端口 |
| `MATH_ASSISTANT_DB_URL` | 后端数据库 URL |
| `MATH_ASSISTANT_SECRET_KEY` | JWT 密钥 |

---

## License

MIT
