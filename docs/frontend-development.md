# NL2SQL Agent — 前端开发文档

> 基于 [nl2sql-agent-requirements.md](../nl2sql-agent-requirements.md) 生成。
> 前端目标：极简 UI，核心展示 Agent 的 SQL 生成 → 执行 → 翻译全流程。

---

## 1. 技术选型

| 类别 | 选择 | 理由 |
|------|------|------|
| 构建工具 | **Vite** | 快速 HMR，零配置支持 React + TS，与仓库现有项目一致 |
| 语言 | **TypeScript** | 类型安全，与后端 Python 形成互补 |
| UI 框架 | **原生 CSS** | 需求明确"极简 UI"，不引入组件库，避免过度工程化 |
| SQL 高亮 | **highlight.js** | 轻量（~10KB gzip），内置 SQL 语法支持，零配置 |
| HTTP 客户端 | **fetch** (原生) | 仅一个 SSE 端点 + 少量 REST 调用，无需 axios |
| SSE 流式 | **EventSource** (原生) | 浏览器原生支持，自动重连，完美匹配后端 SSE |
| 路由 | **不需要** | 单页应用，无对话历史，无需多页面 |
| 状态管理 | **React Context + useReducer** | 状态简单（单个查询流程），无需 Redux/Zustand |
| 表格 | **原生 `<table>` + CSS** | 结果集简单，无需 ag-grid 等重型表格库 |

**不引入的依赖及理由：**

- **Tailwind CSS** — 需求要求极简，原生 CSS 足够且更轻量，不引入额外构建依赖
- **Axios** — 仅一个 POST + 一个 GET 端点，fetch 完全够用
- **Ant Design / MUI** — 重型组件库与极简目标冲突
- **Redux / Zustand** — 状态流简单（单次查询的线性流程），过度设计
- **React Router** — 单页应用，无路由需求

---

## 2. 项目结构

```
nl2sql-agent/frontend/
├── index.html                  # 入口 HTML
├── package.json
├── tsconfig.json
├── vite.config.ts
├── public/
│   └── favicon.ico
└── src/
    ├── main.tsx                # React 入口
    ├── App.tsx                 # 根组件，组装布局
    ├── App.css                 # 全局样式
    ├── types/
    │   └── index.ts            # 共享类型定义
    ├── context/
    │   └── QueryContext.tsx     # 查询状态 Context + Reducer
    ├── hooks/
    │   └── useSSE.ts           # SSE 连接 Hook
    ├── services/
    │   └── api.ts              # REST API 封装 (POST /query, GET /health)
    ├── components/
    │   ├── QueryInput.tsx       # 输入框 + 提交按钮
    │   ├── QueryInput.css
    │   ├── StatusBar.tsx        # Agent 状态指示器 (流式进度)
    │   ├── StatusBar.css
    │   ├── SqlDisplay.tsx       # SQL 代码高亮展示
    │   ├── SqlDisplay.css
    │   ├── ResultTable.tsx      # 查询结果表格
    │   ├── ResultTable.css
    │   ├── AnswerCard.tsx       # 自然语言回答卡片
    │   ├── AnswerCard.css
    │   ├── ErrorDisplay.tsx     # 错误/重试信息展示
    │   └── ErrorDisplay.css
    └── vite-env.d.ts
```

---

## 3. 类型定义

```typescript
// src/types/index.ts

/** Agent 执行阶段（对应后端 LangGraph 节点） */
export type AgentPhase =
  | 'idle'           // 等待输入
  | 'analyzing'      // 判断问题边界 (F4)
  | 'generating'     // 生成 SQL (F1 step 2)
  | 'executing'      // 执行 SQL (F1 step 3)
  | 'translating'    // 翻译结果为自然语言 (F1 step 4)
  | 'retrying'       // SQL 错误自修复重试中 (F3)
  | 'done'           // 完成
  | 'error';         // 失败（超过重试上限）

/** SSE 推送的单条事件 */
export interface AgentEvent {
  phase: AgentPhase;
  /** 用户原始问题 */
  question?: string;
  /** 生成的 SQL */
  sql?: string;
  /** 执行结果（行数据数组） */
  rows?: Record<string, unknown>[];
  /** 查询结果列名 */
  columns?: string[];
  /** 自然语言回答 */
  answer?: string;
  /** 错误信息 */
  error?: string;
  /** 当前重试次数 */
  retry_count?: number;
  /** 是否为非数据查询（闲聊等） */
  is_chitchat?: boolean;
}

/** 查询状态 */
export interface QueryState {
  phase: AgentPhase;
  question: string;
  sql: string | null;
  rows: Record<string, unknown>[] | null;
  columns: string[] | null;
  answer: string | null;
  error: string | null;
  retryCount: number;
  isChitchat: boolean;
}
```

---

## 4. SSE 流式输出设计 (F5)

### 4.1 协议

后端 FastAPI 通过 SSE (`text/event-stream`) 推送 JSON 事件。每个事件对应一个 `AgentEvent`。

```
POST /api/query
Content-Type: application/json
Body: { "question": "上个月销售额最高的三个产品是什么" }

Response: text/event-stream
---
event: phase
data: {"phase": "analyzing", "question": "上个月销售额最高的三个产品是什么"}

event: phase
data: {"phase": "generating"}

event: phase
data: {"phase": "executing", "sql": "SELECT ..."}

event: phase
data: {"phase": "translating", "rows": [...], "columns": [...]}

event: phase
data: {"phase": "done", "answer": "上个月销售额最高的三个产品是..."}
```

### 4.2 useSSE Hook 设计

```typescript
// src/hooks/useSSE.ts
// 职责：
// 1. 创建 POST 请求，接收 ReadableStream
// 2. 按行解析 SSE（\n\n 分隔），提取 data 字段
// 3. 解析 JSON 后 dispatch 到 QueryContext
// 4. 处理连接断开、错误重连
// 5. 返回 { connect, disconnect, isConnected }
```

**关键实现细节：**
- 使用 `fetch` 发起 POST，读取 `response.body.getReader()` 手动解析 SSE（因为浏览器原生 `EventSource` 不支持 POST 请求体）
- SSE 解析规则：按 `\n\n` 分割事件，识别 `data:` 行，JSON.parse 后 dispatch
- 连接中止：通过 `AbortController` 实现前端主动取消
- 错误处理：网络断开时更新 phase 为 `error`，显示友好提示

---

## 5. 状态管理设计

### 5.1 Reducer 动作

```typescript
type QueryAction =
  | { type: 'START'; question: string }
  | { type: 'PHASE_UPDATE'; event: AgentEvent }
  | { type: 'RESET' }
  | { type: 'ERROR'; error: string };
```

### 5.2 状态流转

```
idle → analyzing → generating → executing → translating → done
                                                    ↓ (retry ≤ 3)
                                                   retrying → generating → ...
                                                    ↓ (retry > 3)
                                                   error
idle → analyzing → done  (闲聊 F4)
```

### 5.3 Context 暴露

```typescript
// QueryContext 提供：
// - state: QueryState          (当前状态)
// - dispatch: Dispatch          (更新状态)
// - submitQuery: (q: string) => void  (发起查询)
// - resetQuery: () => void      (重置状态)
```

---

## 6. 组件设计

### 6.1 组件树

```
App
├── Header (Logo + 标题)
├── QueryInput
│   ├── <textarea> 或 <input>
│   └── <button> 提交
├── StatusBar          (phase !== 'idle' 时显示)
│   └── 阶段指示器: [分析] → [生成SQL] → [执行] → [翻译] → [完成]
├── SqlDisplay         (sql 存在时显示)
│   └── <pre><code> + highlight.js
├── ResultTable        (rows 存在时显示)
│   └── <table> 原生表格
├── AnswerCard         (answer 存在时显示)
│   └── Markdown 风格的自然语言回答
└── ErrorDisplay       (error 存在时显示)
    └── 错误消息 + 重试信息
```

### 6.2 组件职责

| 组件 | 职责 | 关键行为 |
|------|------|----------|
| `QueryInput` | 用户输入自然语言问题 | 支持 Enter 提交，loading 时禁用，placeholder 示例问题 |
| `StatusBar` | 展示 Agent 当前阶段 | 显示为步骤条（step indicator），当前步骤高亮，已完成步骤打勾 |
| `SqlDisplay` | 展示生成的 SQL | 使用 highlight.js 语法高亮，一键复制按钮 |
| `ResultTable` | 展示查询结果 | 原生 `<table>`，支持横向滚动（宽表），空状态提示 |
| `AnswerCard` | 展示自然语言回答 | 简洁卡片样式，区分数据查询回答和闲聊回答 |
| `ErrorDisplay` | 展示错误信息 | 显示错误详情 + 重试次数，提供"重新提问"按钮 |

---

## 7. 页面布局

```
┌─────────────────────────────────────────────────┐
│  🔍 NL2SQL Agent                                │
│  用自然语言查询你的数据                            │
├─────────────────────────────────────────────────┤
│                                                  │
│  ┌─────────────────────────────────────────────┐│
│  │ 输入你的问题...                     [ 查询 ] ││
│  └─────────────────────────────────────────────┘│
│                                                  │
│  示例: "上个月销售额最高的三个产品是什么" •        │
│        "哪些客户的订单总数超过 10 单" •            │
│        "退货率最高的品类是哪个"                     │
│                                                  │
├─────────────────────────────────────────────────┤
│  [分析] ──→ [生成SQL] ──→ [执行] ──→ [翻译] ──→ ✓│  ← StatusBar
├─────────────────────────────────────────────────┤
│                                                  │
│  ┌ SQL ───────────────────────────────────────┐ │
│  │ SELECT p.name, SUM(oi.amount) as total      │ │
│  │ FROM order_items oi                         │ │
│  │ JOIN products p ON ...                      │ │
│  │ WHERE o.order_date >= ...                   │ │
│  │ GROUP BY p.name                             │ │
│  │ ORDER BY total DESC                         │ │
│  │ LIMIT 3;                                    │ │
│  │                                    [复制]   │ │
│  └─────────────────────────────────────────────┘ │
│                                                  │
│  ┌ 查询结果 ──────────────────────────────────┐ │
│  │ name          │ total_sales                 │ │
│  │───────────────┼─────────────────────────────│ │
│  │ iPhone 15     │ ¥1,234,567                  │ │
│  │ MacBook Pro   │ ¥987,654                    │ │
│  │ AirPods Pro   │ ¥876,543                    │ │
│  └─────────────────────────────────────────────┘ │
│                                                  │
│  ┌ 回答 ──────────────────────────────────────┐ │
│  │ 上个月销售额最高的三个产品分别是：          │ │
│  │ 1. iPhone 15 (¥1,234,567)                   │ │
│  │ 2. MacBook Pro (¥987,654)                   │ │
│  │ 3. AirPods Pro (¥876,543)                   │ │
│  └─────────────────────────────────────────────┘ │
│                                                  │
└─────────────────────────────────────────────────┘
```

### 布局要点

- **单列居中布局**，最大宽度 `720px`，不分散注意力
- **输入区置顶**，始终可见（sticky 或固定位置）
- **结果区从上到下**按流程展开：SQL → 表格 → 回答
- **流式阶段**每个组件在其数据到达时才渲染，配合 CSS transition 平滑出现
- **颜色编码**：SQL 代码块用深色背景，表格用浅色斑马条纹，回答卡片用蓝色左边框
- **响应式**：移动端最大宽度 100%，横向滚动表格

---

## 8. 错误处理 & 边界状态

| 场景 | 前端行为 |
|------|----------|
| 网络断开 | ErrorDisplay 显示"网络连接失败"，提供重试按钮 |
| SSE 流中断 | 显示已接收的部分结果 + 错误提示 |
| SQL 执行失败 (retry ≤ 3) | StatusBar 显示 "重试中 (2/3)"，不清空已有 SQL |
| SQL 执行失败 (retry > 3) | ErrorDisplay 显示"查询失败，请尝试换一种问法" |
| 闲聊问题 | AnswerCard 直接显示 LLM 回答，不展示 SqlDisplay/ResultTable |
| 空结果集 | ResultTable 显示"查询无结果"，AnswerCard 说明情况 |
| 输入为空 | 按钮置灰，不允许提交 |
| 查询进行中再次提交 | 按钮置灰并显示"查询中..."，阻止重复提交 |

---

## 9. API 接口约定

### POST /api/query

**请求：**
```json
{ "question": "上个月销售额最高的三个产品是什么" }
```

**响应：** SSE stream (`text/event-stream`)，每条事件格式 `AgentEvent`（JSON）。

### GET /api/health

**响应：**
```json
{ "status": "ok", "db_loaded": true }
```

用于前端启动时检查后端和数据库是否就绪。

### GET /api/db/schema (可选)

**响应：**
```json
{
  "tables": [
    {
      "name": "customers",
      "columns": [
        { "name": "id", "type": "INTEGER" },
        { "name": "name", "type": "TEXT" }
      ]
    }
  ]
}
```

用于前端展示数据库概况（帮助用户了解可查询的数据范围）。

---

## 10. 开发任务拆分

| # | 任务 | 产出 | 预估复杂度 |
|---|------|------|------------|
| 1 | **项目初始化** | Vite + React + TS 脚手架，目录结构，CSS 变量，全局样式 | 低 |
| 2 | **类型定义 + Context** | `types/index.ts`, `QueryContext.tsx`, reducer 逻辑 | 低 |
| 3 | **SSE Hook** | `useSSE.ts`, 手动解析 SSE 流，dispatch 事件 | 中 |
| 4 | **API 服务层** | `api.ts`, POST/GET 封装，health check | 低 |
| 5 | **QueryInput 组件** | 输入框 + 提交按钮 + 示例问题 | 低 |
| 6 | **StatusBar 组件** | 阶段指示器步骤条，动画过渡 | 低 |
| 7 | **SqlDisplay 组件** | highlight.js 集成，SQL 高亮，复制按钮 | 中 |
| 8 | **ResultTable 组件** | 原生表格，空状态，横向滚动 | 低 |
| 9 | **AnswerCard 组件** | 自然语言回答卡片，区分数据/闲聊 | 低 |
| 10 | **ErrorDisplay 组件** | 错误展示，重试信息，状态重置 | 低 |
| 11 | **App 组装 + 布局** | 组件拼装，全局 CSS，响应式适配 | 中 |
| 12 | **集成验证** | 对接后端 SSE，完整流程走通，边界状态测试 | 中 |

---

## 11. 注意事项

1. **SSE 手动解析是核心难点** — 浏览器 `EventSource` 不支持 POST，必须用 `fetch` + `ReadableStream` 手动解析 SSE 格式。注意处理分包问题（一个 chunk 可能包含不完整的事件）。
2. **highlight.js 按需加载** — 仅导入 SQL 语言包，避免打包整个库（~500KB → ~10KB）。
3. **状态不要"倒退"** — 流式阶段是单向的（idle → ... → done），reducer 应拒绝非法的状态倒退。
4. **卸载时清理** — 组件卸载时必须 `AbortController.abort()`，避免内存泄漏。
5. **CSS 设计令牌** — 提前定义 CSS 变量（颜色、间距、圆角），保证极简风格的一致性。
