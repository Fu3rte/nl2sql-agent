# NL2SQL Agent — 多 Agent 并行开发指南

> 面向 Claude Code subagent 协作开发的协调文档。
> 使用者：你（主 Agent）+ 多个 subagent 并行开发前后端。

---

## 1. 项目概述

**NL2SQL Agent** — 自然语言 → SQL → 执行 → 翻译 的单 Agent 应用。

- **后端**：Python + FastAPI + LangGraph + LangChain + SQLite
- **前端**：React + TypeScript + Vite + 原生 CSS
- **LLM**：DeepSeek V4（OpenAI 兼容 API）
- **目标**：入门练手项目，熟悉 Agent 架构 & Tool Calling

详细需求见 `nl2sql-agent-requirements.md`（F1-F7），前后端设计见：
- `docs/backend-development.md`
- `docs/frontend-development.md`

---

## 2. 核心开发原则

### 2.1 契约优先

前后端共享一份 **类型契约**。在任何 agent 开始写代码之前，必须先对齐：

```
SSE 事件格式 (AgentEvent):
{
  "phase": "analyzing" | "generating" | "executing" | "translating" | "retrying" | "done" | "error",
  "question": string | null,
  "sql": string | null,
  "columns": string[] | null,
  "rows": Record<string, unknown>[] | null,
  "answer": string | null,
  "error": string | null,
  "retry_count": number,
  "is_chitchat": boolean
}
```

- 前端 `AgentEvent` interface → `frontend/src/types/index.ts`
- 后端 `_build_sse_payload()` → `main.py`
- **两者字段名、类型必须严格一致**，phase 枚举值完全匹配

### 2.2 可并行拆分

12 个后端任务 + 12 个前端任务，按依赖关系分 3 波并行推进：

| 波次 | 后端 | 前端 | 依赖 |
|------|------|------|------|
| **Wave 1** | T1 项目骨架, T2 配置/状态, T3 数据库层 | T1 项目初始化, T2 类型+Context, T4 API 服务层 | 无 |
| **Wave 2** | T4 Agent graph, T5-T9 五个节点 | T3 SSE Hook, T5-T10 六个组件 | Wave 1 完成 |
| **Wave 3** | T10 SSE 端点, T11 Schema API, T12 集成验证 | T11 App 组装, T12 集成验证 | Wave 2 完成 |

### 2.3 Agent 拆分策略

每个 subagent 的 prompt 必须包含：
1. **任务描述** — 要做什么
2. **输入文件** — 需要读哪些设计文档/已有代码
3. **输出文件清单** — 具体要创建/编辑哪些文件
4. **合约约束** — 涉及的接口/类型定义（不能偏离）
5. **完成标准** — 如何验证该任务完成

---

## 3. 项目结构

```
nl2sql-agent/
├── CLAUDE.md                       # 本文件
├── nl2sql-agent-requirements.md    # 需求文档
├── docs/
│   ├── backend-development.md      # 后端设计
│   └── frontend-development.md     # 前端设计
├── backend/
│   ├── requirements.txt
│   ├── .env.example
│   ├── main.py                     # FastAPI 入口
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py               # pydantic-settings
│   │   ├── database.py             # SQLite + 示例数据
│   │   ├── agent.py                # LangGraph StateGraph
│   │   ├── state.py                # AgentState TypedDict
│   │   ├── models.py               # Pydantic 请求/响应
│   │   ├── nodes/
│   │   │   ├── __init__.py
│   │   │   ├── analyze.py          # 问题分类
│   │   │   ├── generate_sql.py     # SQL 生成 + 自修复
│   │   │   ├── execute.py          # SQL 执行 + 错误捕获
│   │   │   ├── translate.py        # 结果→自然语言
│   │   │   └── chitchat.py         # 闲聊 + 错误兜底
│   │   └── tools/
│   │       ├── __init__.py
│   │       ├── get_tables.py       # @tool: 获取表结构
│   │       └── execute_query.py    # @tool: 执行查询
│   └── data/
│       └── ecommerce.db            # 启动时自动创建
└── frontend/
    ├── index.html
    ├── package.json
    ├── tsconfig.json
    ├── vite.config.ts
    ├── public/
    │   └── favicon.ico
    └── src/
        ├── main.tsx
        ├── App.tsx
        ├── App.css
        ├── vite-env.d.ts
        ├── types/
        │   └── index.ts            # AgentPhase, AgentEvent, QueryState
        ├── context/
        │   └── QueryContext.tsx     # Context + Reducer
        ├── hooks/
        │   └── useSSE.ts           # SSE 手动解析 Hook
        ├── services/
        │   └── api.ts              # fetch 封装
        └── components/
            ├── QueryInput.tsx/css
            ├── StatusBar.tsx/css
            ├── SqlDisplay.tsx/css
            ├── ResultTable.tsx/css
            ├── AnswerCard.tsx/css
            └── ErrorDisplay.tsx/css
```

---

## 4. Agent 任务模板

### 4.1 Wave 1 后端 Agent（骨架 + 配置 + 数据库）

**输入文档**：`docs/backend-development.md` §1-3, §7, §8, §10
**输出文件**：
- `backend/requirements.txt`
- `backend/.env.example`
- `backend/main.py`（骨架：CORS + lifespan + health endpoint）
- `backend/app/__init__.py`
- `backend/app/config.py`
- `backend/app/state.py`
- `backend/app/models.py`
- `backend/app/database.py`
- `backend/app/nodes/__init__.py`
- `backend/app/tools/__init__.py`

**合约约束**：
- `AgentState` 字段必须与 §3.1 完全一致
- Pydantic models 与 §3.2 一致
- DB schema 与 §7.1 一致（4 张表，精确 DDL）
- `Settings` 配置项与 §8.1 一致

**完成标准**：
- `main.py` 可启动（`uvicorn main:app`），`/api/health` 返回 `{"status":"ok","db_loaded":true}`
- 首次启动自动创建 `ecommerce.db` 并插入示例数据
- `get_schema_text()` 返回完整表结构文本

---

### 4.2 Wave 1 前端 Agent（脚手架 + 类型 + API 层）

**输入文档**：`docs/frontend-development.md` §1-3, §9
**输出文件**：
- `frontend/package.json`
- `frontend/tsconfig.json`
- `frontend/vite.config.ts`
- `frontend/index.html`
- `frontend/src/main.tsx`
- `frontend/src/App.tsx`（骨架）
- `frontend/src/App.css`（CSS 变量 + 全局样式）
- `frontend/src/vite-env.d.ts`
- `frontend/src/types/index.ts`
- `frontend/src/context/QueryContext.tsx`
- `frontend/src/services/api.ts`

**合约约束**：
- `AgentPhase` 联合类型与 §3 完全一致
- `AgentEvent` 接口字段与 SSE 契约一致
- `QueryState` 与 `AgentEvent` 字段对应
- Reducer 拒绝非法状态倒退

**完成标准**：
- `npm run dev` 启动无报错
- `GET /api/health` 封装可用
- TypeScript 编译零错误

---

### 4.3 Wave 2 后端 Agent（Agent Graph + 5 个节点）

**输入文档**：`docs/backend-development.md` §4, §6
**输入文件**（已存在）：
- `backend/app/state.py`
- `backend/app/config.py`
- `backend/app/database.py`
- `backend/app/models.py`

**输出文件**：
- `backend/app/agent.py`（StateGraph 构建 + 编译 + LLM 实例）
- `backend/app/nodes/analyze.py`
- `backend/app/nodes/generate_sql.py`
- `backend/app/nodes/execute.py`
- `backend/app/nodes/translate.py`
- `backend/app/nodes/chitchat.py`

**合约约束**：
- StateGraph 结构与 §4.1 图一致（6 节点 + 2 条件路由 + START/END）
- 条件路由函数签名与 §4.4 一致
- 每个节点的输入/输出与 §4.2 表一致
- SQL 解析：用正则提取 markdown 代码块中的 SQL
- 写操作拦截：仅放行 SELECT/WITH
- 重试上限：3 次（`settings.max_retries`）
- Schema 注入方式：system prompt 直接嵌入（非 Tool Calling）

**完成标准**：
- `agent_graph = build_graph()` 可编译不报错
- 每个节点函数签名正确（接收 state，返回 dict 更新）
- `astream_events()` 可正常迭代

---

### 4.4 Wave 2 前端 Agent（SSE Hook + 6 个组件）

**输入文档**：`docs/frontend-development.md` §4-6, §4.2
**输入文件**（已存在）：
- `frontend/src/types/index.ts`
- `frontend/src/context/QueryContext.tsx`
- `frontend/src/services/api.ts`

**输出文件**：
- `frontend/src/hooks/useSSE.ts`
- `frontend/src/components/QueryInput.tsx` + `.css`
- `frontend/src/components/StatusBar.tsx` + `.css`
- `frontend/src/components/SqlDisplay.tsx` + `.css`
- `frontend/src/components/ResultTable.tsx` + `.css`
- `frontend/src/components/AnswerCard.tsx` + `.css`
- `frontend/src/components/ErrorDisplay.tsx` + `.css`

**合约约束**：
- SSE 解析：`fetch` + `ReadableStream` + 按 `\n\n` 分割 + 识别 `data:` 行
- `useSSE` 返回 `{ connect, disconnect, isConnected }`
- highlight.js 仅导入 SQL 语言包
- 组件卸载时必须 `AbortController.abort()`
- 状态只能单向流转（拒绝倒退）

**完成标准**：
- 每个组件根据 `QueryState` 对应字段条件渲染
- SSE Hook 可正确解析后端推送的每一条事件
- TypeScript 编译零错误

---

### 4.5 Wave 3 后端 Agent（SSE 端点 + Schema API + 集成）

**输入文档**：`docs/backend-development.md` §5, §9, §10
**输入文件**（已存在）：所有 Wave 1/2 产物

**输出文件**：
- `backend/main.py`（补充 SSE endpoint 完整实现）
- `backend/app/agent.py`（如有调整）

**合约约束**：
- SSE 格式：`event: phase\ndata: {json}\n\n`
- SSE headers：`Cache-Control: no-cache`, `Connection: keep-alive`, `X-Accel-Buffering: no`
- `_build_sse_payload()` 输出字段与前端 `AgentEvent` 严格对齐
- `GET /api/db/schema` 返回格式与 §9.3 一致

**完成标准**：
- `POST /api/query` 返回 SSE stream
- 完整查询流程：analyzing → generating → executing → done
- 错误重试流程：executing → retrying → generating → ... → error
- 闲聊分流：analyzing → done（is_chitchat=true）

---

### 4.6 Wave 3 前端 Agent（App 组装 + 集成）

**输入文档**：`docs/frontend-development.md` §6, §7
**输入文件**（已存在）：所有 Wave 1/2 产物

**输出文件**：
- `frontend/src/App.tsx`（完整组装）
- `frontend/src/App.css`（完善布局样式）

**合约约束**：
- 布局：单列居中 max-width 720px
- 组件渲染条件：按 phase 和字段存在性
- CSS 设计令牌（变量）在前

**完成标准**：
- 完整 SSE 流式查询走通
- 6 种场景覆盖：正常查询、闲聊、空结果、重试成功、重试失败、网络错误
- 响应式：移动端可用

---

## 5. 并行调度命令

### 启动 Wave 1（可同时派发 2 个 agent）

```
主 Agent 读取 docs/backend-development.md + docs/frontend-development.md
  → 派发 Agent A: 按 §4.1 模板开发后端骨架
  → 派发 Agent B: 按 §4.2 模板开发前端脚手架
  → 两者无依赖，完全并行
```

### 启动 Wave 2（可同时派发 2 个 agent）

```
Wave 1 验证通过后:
  → 派发 Agent C: 按 §4.3 模板开发 Agent Graph + 5 节点
  → 派发 Agent D: 按 §4.4 模板开发 SSE Hook + 6 组件
  → 两者无依赖，完全并行（合约已在 Wave 1 定义）
```

### 启动 Wave 3（需先后端再前端，或同时派发）

```
Wave 2 验证通过后:
  → 派发 Agent E: 按 §4.5 模板完成 SSE 端点
  → 派发 Agent F: 按 §4.6 模板组装前端
  → 后端 SSE 就绪后前端可联调
```

---

## 6. 关键约束速查

### 6.1 后端约束

| 约束 | 详情 |
|------|------|
| LLM API | `ChatOpenAI` 指向 `https://api.deepseek.com/v1`，model=`deepseek-chat` |
| SQL 生成温度 | `temperature=0.0`（确保稳定） |
| 闲聊/翻译温度 | `temperature=0.3` |
| Schema 注入 | system prompt 直接嵌入，**不用** Tool Calling |
| SQL 提取 | 正则：````sql ... ``` `` 或纯文本 |
| 写操作拦截 | 仅放行 `SELECT` / `WITH` 开头 |
| 重试上限 | 3 次 |
| 结果截断 | translate 节点只传前 20 行给 LLM |
| LangGraph 版本 | `langgraph>=0.2.0` |
| SSE 事件尾 | 每条以 `\n\n` 结尾 |

### 6.2 前端约束

| 约束 | 详情 |
|------|------|
| SSE 方式 | `fetch` + `ReadableStream`（**不用** `EventSource`，因为要 POST） |
| SQL 高亮 | `highlight.js`，仅导入 SQL 语言包 |
| 状态管理 | React Context + useReducer，无外部库 |
| 样式 | 原生 CSS，CSS 变量定义设计令牌，无 Tailwind |
| 路由 | 不需要（单页应用） |
| 取消请求 | `AbortController`，组件卸载时 abort |
| 最大宽度 | `720px` 单列居中 |
| 状态流向 | 单向：idle → analyzing → generating → executing → translating → done |

### 6.3 共享契约（前后端必须对齐）

```
phase 枚举: idle | analyzing | generating | executing | translating | retrying | done | error

SSE data JSON 字段:
  phase: string (必含)
  question: string | null
  sql: string | null
  columns: string[] | null
  rows: Record<string, unknown>[] | null
  answer: string | null
  error: string | null
  retry_count: number
  is_chitchat: boolean
```

---

## 7. 开发顺序建议

```
Phase 0: 阅读本文 + 两份设计文档 + git init 首次提交（主 Agent）
         ↓
Phase 1: Wave 1 并行 — 后端骨架 ⚡ 前端脚手架    [预计 2 agent 同时]
         ↓
Phase 2: Wave 2 并行 — 后端节点 ⚡ 前端组件      [预计 2 agent 同时]
         ↓
Phase 3: Wave 3 并行 — 后端 SSE ⚡ 前端组装      [预计 2 agent 同时]
         ↓
Phase 4: 集成联调 + 6 场景端到端测试              [主 Agent 直接操作]
```

---

## 8. Git 仓库 & 提交规范

### 8.1 初始化时机

在 **Wave 1 开始前** 必须完成 `git init` + 首次提交，否则 subagent 产物无版本追踪，后续调试无法回溯。

### 8.2 .gitignore 模板

```gitignore
# Python
__pycache__/
*.py[cod]
*.egg-info/
.venv/
venv/

# Node
node_modules/
dist/

# Env & secrets
.env
.env.local

# DB (自动生成，不提交)
*.db

# IDE
.idea/
.vscode/
*.swp
```

### 8.3 提交策略

| 阶段 | 提交者 | Commit 内容 | 分支 |
|------|--------|-------------|------|
| **Wave 0** | 主 Agent | `git init`、`.gitignore`、`docs/` 设计文档 | `main` |
| **Wave 1 完成** | 主 Agent | 后端骨架 + 前端脚手架（验证通过后一起提交） | `main` |
| **Wave 2 完成** | 主 Agent | Agent Graph + 5节点 + SSE Hook + 6组件 | `main` |
| **Wave 3 完成** | 主 Agent | SSE 端点 + App 组装（联调通过后提交） | `main` |
| **Bug 修复** | 主 Agent | 单次修复 → 独立 commit | `main` |

### 8.4 提交原则

- **每个 Wave 完成且验证通过后才提交**，不要提交半成品
- **Commit message 格式**：`feat(waveN): 简短描述`，如 `feat(wave1): 后端骨架 + 前端脚手架`
- **禁止提交**：`.env`、`ecommerce.db`、`node_modules/`、`__pycache__/`、任何 API key
- **Subagent 不提交**：subagent 只写代码不执行 git 操作，所有提交由主 Agent 统一完成
- **提交前检查**：主 Agent 必须 `git diff --staged` 确认无敏感文件后才可以 commit

### 8.5 远程仓库（可选）

如需推送到 GitHub：
```bash
gh repo create nl2sql-agent --private --source=. --push
```
推送时机：全部 Wave 完成并通过 6 场景端到端测试后。

---

## 9. Subagent 派发要求

每次派发 subagent 时，prompt 必须包含：

1. **上下文**：这个项目是什么（NL2SQL Agent），当前处于哪个 Wave
2. **阅读清单**：需要读哪些文档/已有代码文件（给出具体路径）
3. **产出清单**：要创建/修改的文件完整列表
4. **合约**：涉及的接口/类型定义（复制具体代码，不要只说"参考§x.x"）
5. **不做什么**：明确排除范围（如"不要写 SSE endpoint，那是 Wave 3 的事"）

示例 prompt 框架：
```
你在开发 NL2SQL Agent 项目的 [Wave N / 任务名]。
项目背景：[一段话简述]

请先阅读以下文件：
- docs/[xxx].md 的 §X-Y
- [已有代码文件路径]

然后创建/修改以下文件：
- [文件1]：[描述]
- [文件2]：[描述]

必须遵守的合约：
[粘贴具体的类型定义/接口]

不要做：[明确排除]
```
