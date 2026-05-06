# NL2SQL Agent — 后端开发文档

> 基于 [nl2sql-agent-requirements.md](../nl2sql-agent-requirements.md) 和 [前端开发文档](frontend-development.md) 生成。
> 后端目标：单 Agent 架构，LangGraph 状态机驱动 SQL 生成 → 执行 → 翻译全流程，SSE 流式推送。

---

## 1. 技术选型

| 类别 | 选择 | 理由 |
|------|------|------|
| API 框架 | **FastAPI** | 原生支持异步、SSE StreamingResponse、Pydantic 模型验证、自动 OpenAPI 文档 |
| Agent 框架 | **LangGraph** | StateGraph 状态机，显式节点+边控制流，天然支持自修复循环，`astream_events()` 完美匹配 SSE |
| LLM 调用 | **LangChain** | ChatOpenAI 兼容 Anthropic API 格式，`bind_tools()` 标准 Tool Calling，SQLDatabase 辅助 |
| 数据库 | **SQLite** | 零配置、文件级、内置示例数据，启动即用 |
| SQL 工具包 | **自定义 @tool** | 仅需 get_tables + execute_query 两个工具，比 SQLDatabaseToolkit 更透明，便于理解 Tool Calling 机制 |
| 配置管理 | **pydantic-settings** | BaseSettings 自动读取 .env / 环境变量，与现有学习代码一致 |
| 异步 | **async/await** | FastAPI 原生异步，LLM 调用和流式输出均为 async |
| 包管理 | **pip + requirements.txt** | 简单，无额外工具依赖 |

**不引入的依赖及理由：**

- **SQLDatabaseToolkit** — 4 个工具过于冗余，练手项目已决定用自定义 @tool 深入理解 Tool Calling
- **SqliteSaver / checkpoint** — 需求明确不做对话历史管理，无需持久化状态
- **Alembic / SQLAlchemy ORM** — SQLite 示例数据用原生 SQL 初始化即可，无需 ORM
- **Celery / 消息队列** — 单 Agent 同步流，不需要后台任务

---

## 2. 项目结构

```
nl2sql-agent/backend/
├── requirements.txt
├── .env.example               # 环境变量模板 (LLM API key 等)
├── main.py                    # FastAPI 入口: CORS, lifespan, /api/query (SSE), /api/health
├── app/
│   ├── __init__.py
│   ├── config.py              # Settings: LLM 配置, DB 路径, 重试上限
│   ├── database.py            # SQLite 连接管理 + 示例数据初始化 (F6)
│   ├── agent.py               # StateGraph 构建、编译、调用入口
│   ├── state.py               # AgentState TypedDict 定义
│   ├── models.py              # Pydantic 请求/响应模型
│   ├── nodes/
│   │   ├── __init__.py
│   │   ├── analyze.py         # analyze_question: LLM 判断问题边界 (F4)
│   │   ├── generate_sql.py    # generate_sql: LLM 生成 SQL (支持重试上下文)
│   │   ├── execute.py         # execute_sql: 执行 SQL + 错误捕获
│   │   ├── translate.py       # translate_result: LLM 结果→自然语言
│   │   └── chitchat.py        # 闲聊回答 + 错误兜底响应
│   └── tools/
│       ├── __init__.py
│       ├── get_tables.py      # @tool: 获取所有表结构 (表名/列/类型/示例行)
│       └── execute_query.py   # @tool: 执行 SQL 查询 (读操作)
└── data/
    └── ecommerce.db           # 电商示例数据库 (首次启动自动创建)
```

---

## 3. 核心类型定义

### 3.1 AgentState (LangGraph 状态)

```python
# app/state.py
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class AgentState(TypedDict):
    """LangGraph 共享状态，流经所有节点。"""

    # 消息历史 (add_messages 自动追加)
    messages: Annotated[list[BaseMessage], add_messages]

    # 当前阶段 — 对应前端 AgentPhase
    phase: str
    # "analyzing" | "generating" | "executing" | "translating"
    # | "retrying" | "done" | "error"

    # 用户输入
    question: str

    # 问题分类 (F4)
    is_data_query: bool

    # SQL 生成
    sql: str | None

    # 查询结果
    columns: list[str] | None
    rows: list[dict] | None

    # 最终回答
    answer: str | None

    # 错误处理 (F3)
    error: str | None
    retry_count: int
```

### 3.2 Pydantic 模型

```python
# app/models.py
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, description="用户的自然语言问题")


class TableInfo(BaseModel):
    name: str
    columns: list[dict]  # [{"name": "id", "type": "INTEGER"}, ...]


class HealthResponse(BaseModel):
    status: str
    db_loaded: bool


class SchemaResponse(BaseModel):
    tables: list[TableInfo]
```

### 3.3 SSE 事件格式

SSE 推送的 data 字段与前端 `AgentEvent` 接口一一对应：

```json
{
  "phase": "generating",
  "question": "上个月销售额最高的三个产品是什么",
  "sql": null,
  "rows": null,
  "columns": null,
  "answer": null,
  "error": null,
  "retry_count": 0,
  "is_chitchat": false
}
```

每个节点仅更新相关字段，前端按 phase 和字段是否存在决定展示内容。

---

## 4. LangGraph Agent 设计

### 4.1 状态图结构

```
START
  │
  ▼
analyze_question ────────── is_data_query=false ──→ generate_chitchat_answer ──→ END
  │
  │ is_data_query=true
  ▼
generate_sql
  │
  ▼
execute_sql ──── success ────→ translate_result ──→ END
  │                              (phase=done)
  │ error & retry_count < 3
  └────────────────────────→ generate_sql (phase=retrying, 携带错误信息)
  │ error & retry_count >= 3
  └────────────────────────→ error_response ──→ END
                              (phase=error)
```

### 4.2 节点职责

| 节点 | 输入 | 处理逻辑 | 输出 |
|------|------|----------|------|
| `analyze_question` | `question` | LLM 判断问题是否需要数据库查询，返回 `is_data_query` | `phase=analyzing`, `is_data_query` |
| `generate_chitchat_answer` | `question` | LLM 直接回答闲聊问题 | `phase=done`, `answer` |
| `generate_sql` | `question`, `error`(重试时), `sql`(上次) | LLM 读取表结构 → 生成 SQL。重试时 prompt 携带上次错误信息 | `phase=generating/retrying`, `sql` |
| `execute_sql` | `sql` | 执行 SQL，捕获异常 | `phase=executing`, `columns`, `rows` 或 `error`, `retry_count++` |
| `translate_result` | `question`, `sql`, `columns`, `rows` | LLM 将查询结果翻译为自然语言回答 | `phase=done`, `answer` |
| `error_response` | `error`, `retry_count` | 构造友好错误提示 | `phase=error`, `answer` |

### 4.3 Tool Calling 设计 (F1)

Agent 拥有 2 个工具，通过 `llm.bind_tools()` 绑定：

**工具 1: `get_tables`**
```python
@tool
def get_tables() -> str:
    """获取数据库中所有表的名称、字段定义和示例数据。
    在生成 SQL 之前必须调用此工具以了解可用的表和字段。"""
```
- 返回: 所有表的 CREATE TABLE 语句 + 每个表前3行数据
- 用途: 让 LLM 在生成 SQL 前了解 schema

**工具 2: `execute_query`**
```python
@tool
def execute_query(sql: str) -> str:
    """在 SQLite 数据库上执行一条 SELECT 查询。
    仅支持读操作 (SELECT)，不支持 INSERT/UPDATE/DELETE/DROP 等写操作。"""
```
- 写操作拦截: 匹配非 SELECT 语句时返回错误
- 用途: 让 Agent 能够验证/探索数据

**Tool Calling 流程** (在 `generate_sql` 节点内):
1. `llm.bind_tools([get_tables, execute_query])`
2. LLM 决定先调用 `get_tables()` 获取 schema
3. LLM 基于 schema 生成 SQL
4. (可选) LLM 调用 `execute_query()` 验证 SQL
5. 节点输出最终 `sql` 到 state

### 4.4 条件路由

```python
# app/agent.py

def route_after_analyze(state: AgentState) -> str:
    """根据问题类型分流。"""
    if state["is_data_query"]:
        return "generate_sql"
    return "generate_chitchat_answer"


def route_after_execute(state: AgentState) -> str:
    """根据执行结果分流：成功/重试/失败。"""
    if state["error"] is None:
        return "translate_result"
    if state["retry_count"] < settings.max_retries:  # 3
        return "generate_sql"
    return "error_response"
```

### 4.5 编译入口

```python
# app/agent.py
from langgraph.graph import StateGraph, START, END
from app.state import AgentState
from app.nodes import analyze, generate_sql, execute, translate, chitchat


def build_graph() -> StateGraph:
    builder = StateGraph(AgentState)

    # 添加节点
    builder.add_node("analyze_question", analyze.run)
    builder.add_node("generate_chitchat_answer", chitchat.run_chitchat)
    builder.add_node("generate_sql", generate_sql.run)
    builder.add_node("execute_sql", execute.run)
    builder.add_node("translate_result", translate.run)
    builder.add_node("error_response", chitchat.run_error)

    # 入口
    builder.add_edge(START, "analyze_question")

    # 条件分流
    builder.add_conditional_edges(
        "analyze_question",
        route_after_analyze,
        {"generate_sql": "generate_sql", "generate_chitchat_answer": "generate_chitchat_answer"},
    )
    builder.add_conditional_edges(
        "execute_sql",
        route_after_execute,
        {
            "translate_result": "translate_result",
            "generate_sql": "generate_sql",
            "error_response": "error_response",
        },
    )

    # 出口
    builder.add_edge("generate_chitchat_answer", END)
    builder.add_edge("translate_result", END)
    builder.add_edge("error_response", END)

    return builder.compile()


# 全局单例
agent_graph = build_graph()
```

---

## 5. SSE 流式输出设计 (F5)

### 5.1 协议

后端通过 FastAPI `StreamingResponse` 推送 SSE 事件，与前端 `useSSE` Hook 的解析逻辑匹配：

```
POST /api/query
Content-Type: application/json
{"question": "上个月销售额最高的三个产品是什么"}

Response: text/event-stream

event: phase
data: {"phase":"analyzing","question":"上个月...","is_chitchat":false}

event: phase
data: {"phase":"generating","sql":"SELECT ..."}

event: phase
data: {"phase":"executing","sql":"SELECT ...","columns":["name","total"],"rows":[...]}

event: phase
data: {"phase":"done","answer":"上个月销售额最高的三个产品是..."}
```

### 5.2 实现方案

使用 LangGraph 的 `astream_events()` API (v2)，在每个节点结束时捕获状态变更并推送：

```python
# main.py
from fastapi.responses import StreamingResponse
import json


@app.post("/api/query")
async def query(request: QueryRequest):
    async def event_stream():
        async for event in agent_graph.astream_events(
            {"question": request.question, ...},
            version="v2",
        ):
            # 只关注节点完成事件
            if event["event"] == "on_chain_end" and "output" in event["data"]:
                state = event["data"]["output"]
                yield format_sse(state)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 nginx 缓冲
        },
    )


def format_sse(state: dict) -> str:
    """将 state 转为 SSE 事件字符串。"""
    payload = {
        "phase": state.get("phase", ""),
        "question": state.get("question"),
        "sql": state.get("sql"),
        "columns": state.get("columns"),
        "rows": state.get("rows"),
        "answer": state.get("answer"),
        "error": state.get("error"),
        "retry_count": state.get("retry_count", 0),
        "is_chitchat": not state.get("is_data_query", True),
    }
    return f"event: phase\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
```

**为什么用 `astream_events` 而不是 `astream`：**
- `astream` 仅在每个节点完成时 yield 一次 state，可能聚合多个事件
- `astream_events` 提供更细粒度的事件回调，可在每个节点边界精确推送
- 前端需要每个 phase 变化都收到一次 SSE 事件，`astream_events` 的 `on_chain_end` 事件正好对应

### 5.3 状态推送时机

| 节点 | 推送的 phase | 关键字段 |
|------|-------------|----------|
| `analyze_question` 完成 | `analyzing` | `question`, `is_chitchat` |
| `generate_sql` 完成 | `generating` / `retrying` | `sql`, `retry_count` |
| `execute_sql` 完成 | `executing` | `sql`, `columns`, `rows` |
| `translate_result` 完成 | `done` | `answer` |
| `generate_chitchat_answer` 完成 | `done` | `answer`, `is_chitchat: true` |
| `error_response` 完成 | `error` | `error`, `retry_count` |

---

## 6. 各节点实现要点

### 6.1 analyze_question (F4 问题边界判断)

```
输入: state.question
LLM prompt: "判断以下问题是否需要查询数据库。仅回答 YES 或 NO。"
解析: YES → is_data_query=true, NO → is_data_query=false
输出: phase=analyzing, is_data_query
```

- 使用 **零温度 (temperature=0)** 确保判断结果稳定
- Prompt 明确分类标准：数据统计/排行/筛选 → YES，问候/闲聊/常识 → NO
- 输出解析需处理 LLM 返回 "YES." / "Yes" / "yes" 等变体

### 6.2 generate_sql (F1 SQL 生成 + F3 自修复)

```
输入: state.question, state.error (重试时), state.sql (上次)
步骤:
  1. 构造 system prompt (表结构 + SQLite 约束 + 输出格式)
  2. LLM 生成 SQL
  3. 解析 LLM 输出，提取 SQL 语句
  4. 基础校验: 非空、包含 SELECT
输出: phase=generating 或 retrying, sql
```

**重试 Prompt 构造 (F3):**
```
上次生成的 SQL: {state.sql}
执行错误: {state.error}
请根据错误信息修正 SQL 并重新生成。只输出 SQL 语句。
```

**表结构注入方式:**
- 方法: 在 system prompt 中直接嵌入 `database.get_schema_text()` 的完整输出
- 不使用 `get_tables` tool 的 Tool Calling（简单场景，直接注入更可靠）
- Schema 文本包含: `CREATE TABLE xxx (...)` + 每个表 3 行示例数据

### 6.3 execute_sql (F1 执行 + F3 错误捕获)

```
输入: state.sql
步骤:
  1. 写操作拦截: 检查 SQL 首 token 是否为 SELECT
  2. 执行: cursor.execute(sql).fetchall()
  3. 提取 columns (cursor.description) 和 rows
失败:
  - 捕获 sqlite3.Error → 设置 state.error, retry_count++
  - 非SELECT语句 → 设置 state.error = "仅支持SELECT查询"
输出: phase=executing, columns, rows 或 error, retry_count
```

**安全检查：**
```python
def is_read_only(sql: str) -> bool:
    """仅允许 SELECT 查询，拒绝写操作。"""
    stripped = sql.strip().upper()
    return stripped.startswith("SELECT") or stripped.startswith("WITH")
```

### 6.4 translate_result (F1 自然语言翻译)

```
输入: state.question, state.sql, state.columns, state.rows
LLM prompt:
  "用户问题: {question}
   执行SQL: {sql}
   查询结果: {rows}
   请用自然语言回答用户的问题，简洁直接。"
输出: phase=done, answer
```

- 对空结果集：LLM 应回复 "查询无结果" 而非编造数据
- 对大数据集：只取前 20 行传给 LLM（避免超出 context window），实际表格展示全量

### 6.5 chitchat (闲聊 + 错误兜底)

**闲聊分支:**
```
输入: state.question
LLM prompt: "你是NL2SQL助手，仅支持数据库查询。请友好回复用户。"
输出: phase=done, answer, is_chitchat=true
```

**错误兜底:**
```
输入: state.error, state.retry_count
输出: phase=error, answer = "抱歉，查询失败了。请尝试换一种问法。(重试{retry_count}次)"
```

---

## 7. 数据库设计 (F6)

### 7.1 示例数据库 Schema

内置电商场景 SQLite 数据库，4 张表：

```sql
-- 用户表
CREATE TABLE customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,              -- 用户名
    email TEXT,                      -- 邮箱
    city TEXT,                       -- 城市
    created_at TEXT DEFAULT (datetime('now'))
);

-- 商品表
CREATE TABLE products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,              -- 商品名
    category TEXT NOT NULL,          -- 品类 (电子产品/服装/食品等)
    price REAL NOT NULL,             -- 单价
    stock INTEGER DEFAULT 0,         -- 库存
    created_at TEXT DEFAULT (datetime('now'))
);

-- 订单表
CREATE TABLE orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    order_date TEXT NOT NULL,        -- 下单日期 (YYYY-MM-DD)
    total_amount REAL NOT NULL,      -- 订单总额
    status TEXT DEFAULT 'completed'  -- 状态 (completed/returned/cancelled)
);

-- 订单明细表
CREATE TABLE order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL REFERENCES orders(id),
    product_id INTEGER NOT NULL REFERENCES products(id),
    quantity INTEGER NOT NULL,       -- 数量
    unit_price REAL NOT NULL,        -- 单价
    subtotal REAL NOT NULL           -- 小计
);
```

### 7.2 示例数据

首次启动时自动生成 ~50 条示例数据：
- 20 个客户 (来自 5 个城市)
- 15 个商品 (分属 3-4 个品类: 电子产品、服装、食品、家居)
- 30 个订单 (覆盖近 3 个月)
- ~80 条订单明细
- 约 5 个退货订单 (status='returned') — 用于"退货率"查询

### 7.3 初始化逻辑

```python
# app/database.py
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "ecommerce.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # 字典式访问
    return conn


def init_db():
    """首次启动时创建表并插入示例数据。"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_connection()
    # 检查是否已初始化
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='customers'"
    )
    if cursor.fetchone():
        conn.close()
        return

    # 执行建表 SQL
    conn.executescript(CREATE_TABLES_SQL)
    # 插入示例数据
    conn.executescript(SEED_DATA_SQL)
    conn.commit()
    conn.close()


def get_schema_text() -> str:
    """获取完整表结构文本，用于注入 LLM prompt。"""
    conn = get_connection()
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()

    schema_parts = []
    for (table_name,) in tables:
        # CREATE TABLE 语句
        ddl = conn.execute(
            f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table_name}'"
        ).fetchone()[0]
        schema_parts.append(ddl + ";")

        # 示例数据 (前3行)
        rows = conn.execute(f"SELECT * FROM {table_name} LIMIT 3").fetchall()
        if rows:
            schema_parts.append(f"-- 示例数据 ({table_name}):")
            for row in rows:
                schema_parts.append(f"--   {dict(row)}")

    conn.close()
    return "\n".join(schema_parts)
```

---

## 8. LLM 接入设计

### 8.1 DeepSeek V4 配置

```python
# app/config.py
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    # LLM
    llm_api_key: str = ""
    llm_model: str = "deepseek-chat"       # DeepSeek V4 模型名
    llm_base_url: str = "https://api.deepseek.com/v1"  # DeepSeek OpenAI兼容端点
    llm_temperature: float = 0.0           # SQL 生成用零温度

    # Agent
    max_retries: int = 3                   # SQL 错误重试上限 (F3)

    # CORS
    cors_origins: list[str] = ["http://localhost:5173"]  # Vite 默认端口


settings = Settings()
```

### 8.2 LLM 实例化

```python
# app/agent.py
from langchain_openai import ChatOpenAI
from app.config import settings

llm = ChatOpenAI(
    model=settings.llm_model,
    api_key=settings.llm_api_key,
    base_url=settings.llm_base_url,
    temperature=settings.llm_temperature,
)
```

DeepSeek API 兼容 OpenAI 格式，`ChatOpenAI` 可直接使用。

---

## 9. API 接口约定

### 9.1 POST /api/query (核心接口)

**请求：**
```
POST /api/query
Content-Type: application/json

{
  "question": "上个月销售额最高的三个产品是什么"
}
```

**响应：** SSE stream (`text/event-stream`)

每条事件格式：
```
event: phase
data: {"phase":"...", "question":"...", "sql":null, "columns":null, "rows":null, "answer":null, "error":null, "retry_count":0, "is_chitchat":false}
```

### 9.2 GET /api/health

**响应：**
```json
{
  "status": "ok",
  "db_loaded": true
}
```

用于前端启动时检查后端和数据库是否就绪。

### 9.3 GET /api/db/schema (可选)

**响应：**
```json
{
  "tables": [
    {
      "name": "customers",
      "columns": [
        {"name": "id", "type": "INTEGER"},
        {"name": "name", "type": "TEXT"},
        {"name": "email", "type": "TEXT"},
        {"name": "city", "type": "TEXT"},
        {"name": "created_at", "type": "TEXT"}
      ]
    }
  ]
}
```

用于前端展示数据库概况（帮助用户了解可查询的数据范围）。

---

## 10. FastAPI 入口设计

```python
# main.py
from contextlib import asynccontextmanager
import json
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.config import settings
from app.database import init_db, get_schema_text
from app.agent import agent_graph
from app.models import QueryRequest, HealthResponse, SchemaResponse


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化数据库。"""
    logger.info("Initializing database...")
    init_db()
    logger.info("Database ready.")
    yield
    logger.info("Shutting down...")


app = FastAPI(title="NL2SQL Agent", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="ok", db_loaded=True)


@app.get("/api/db/schema", response_model=SchemaResponse)
async def db_schema():
    # 解析 schema 文本为结构化数据
    ...


@app.post("/api/query")
async def query(request: QueryRequest):
    async def event_stream():
        async for event in agent_graph.astream_events(
            {
                "question": request.question,
                "messages": [],
                "is_data_query": False,
                "sql": None,
                "columns": None,
                "rows": None,
                "answer": None,
                "error": None,
                "retry_count": 0,
                "phase": "analyzing",
            },
            version="v2",
        ):
            if event["event"] == "on_chain_end":
                output = event["data"].get("output", {})
                if isinstance(output, dict) and "phase" in output:
                    payload = _build_sse_payload(output)
                    yield f"event: phase\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _build_sse_payload(state: dict) -> dict:
    return {
        "phase": state.get("phase", ""),
        "question": state.get("question"),
        "sql": state.get("sql"),
        "columns": state.get("columns"),
        "rows": state.get("rows"),
        "answer": state.get("answer"),
        "error": state.get("error"),
        "retry_count": state.get("retry_count", 0),
        "is_chitchat": not state.get("is_data_query", True),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
```

---

## 11. 错误处理 & 边界状态

| 场景 | 后端行为 |
|------|----------|
| SQL 执行失败 (retry ≤ 3) | `execute_sql` 节点设置 `error` + `retry_count++`，条件路由回到 `generate_sql`，phase=`retrying` |
| SQL 执行失败 (retry > 3) | 条件路由到 `error_response`，返回友好错误消息，phase=`error` |
| 非 SELECT 语句 | `execute_sql` 拦截并设置 error="仅支持SELECT查询"，进入重试流程 |
| 闲聊问题 | `analyze_question` 设置 `is_data_query=false`，路由到 `generate_chitchat_answer` |
| 空结果集 | SQL 正常执行但 rows=[]，`translate_result` 告知 LLM 结果为空的上下文 |
| LLM 返回非标准格式 | 各节点做容错解析：SQL 用正则提取代码块，is_data_query 用 startswith 匹配 |
| LLM API 调用失败 | 节点内 try/except，设置 `error` 字段，由条件路由决定重试或报错 |
| 输入为空 | FastAPI Pydantic 验证自动拦截 `min_length=1`，返回 422 |

---

## 12. 开发任务拆分

| # | 任务 | 产出 | 复杂度 |
|---|------|------|--------|
| 1 | **项目初始化** | requirements.txt, .env.example, main.py 骨架, CORS, health endpoint | 低 |
| 2 | **配置 + 状态定义** | `config.py` (Settings), `state.py` (AgentState), `models.py` (Pydantic) | 低 |
| 3 | **数据库层** | `database.py`: 建表 SQL, 示例数据, get_connection, get_schema_text, init_db | 中 |
| 4 | **LLM 实例化 + Agent graph 骨架** | `agent.py`: ChatOpenAI 配置, StateGraph 搭建, 节点占位, 条件路由 | 中 |
| 5 | **analyze_question 节点** | `nodes/analyze.py`: LLM 问题分类, 边界判断 (F4) | 低 |
| 6 | **generate_sql 节点** | `nodes/generate_sql.py`: schema 注入 prompt, SQL 生成, 重试上下文 (F3) | 中 |
| 7 | **execute_sql 节点** | `nodes/execute.py`: SQL 执行, 写操作拦截, 错误捕获, retry_count 递增 | 中 |
| 8 | **translate_result 节点** | `nodes/translate.py`: 查询结果→自然语言, 空结果处理 | 低 |
| 9 | **chitchat + error 节点** | `nodes/chitchat.py`: 闲聊回答, 错误兜底 | 低 |
| 10 | **SSE 流式输出** | `main.py` SSE endpoint: astream_events → format_sse → StreamingResponse (F5) | 中 |
| 11 | **Schema API** | `GET /api/db/schema` 端点, schema 文本解析为结构化 JSON | 低 |
| 12 | **集成验证** | 端到端测试全部 6 种查询场景, 重试流程, 闲聊分流, 空结果 | 中 |

---

## 13. 注意事项

1. **LangGraph 版本** — 使用 `langgraph>=0.2.0`，API 相对稳定。`astream_events` 是 v2 版本，需确认参数格式。
2. **DeepSeek Tool Calling** — DeepSeek 支持 OpenAI 兼容的 function calling，使用 `llm.bind_tools()` 或直接 prompt 注入 schema。对于本项目的简单场景（单次查询），直接在 system prompt 中注入表结构更可靠，避免 tool calling 的不确定性。
3. **SSE 分包处理** — `astream_events` 的事件粒度正常不会有分包问题，但如果 LLM 响应特别长，确保 `format_sse` 每条事件以 `\n\n` 结尾。
4. **重试状态传递** — 条件路由回到 `generate_sql` 时，state 中的 `error` 和 `sql`(上次) 会被保留，prompt 中需携带这些信息。
5. **SQL 解析健壮性** — LLM 输出的 SQL 可能被包裹在 markdown 代码块中（```sql ... ```），节点需先提取再执行。
6. **写操作防护** — `execute_sql` 节点必须在执行前检查 SQL，仅放行 SELECT/WITH 语句。SQLite 文件层面也可设置只读连接作为双重保护。
7. **LLM 温度设置** — SQL 生成节点使用 temperature=0（确保稳定），闲聊和翻译节点可用 temperature=0.3（增加自然度）。
8. **与前端协议对齐** — SSE 事件的字段名和结构必须与前端 `AgentEvent` 接口严格一致，phase 值必须匹配 `AgentPhase` 联合类型。
