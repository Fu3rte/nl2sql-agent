# Anatomy — NL2SQL Agent

## Backend

| File | Description | ~Tokens |
|------|-------------|---------|
| `backend/requirements.txt` | Python dependencies: FastAPI, LangGraph, LangChain, pydantic-settings | 50 |
| `backend/.env.example` | Environment variable template (LLM API key, model, CORS) | 50 |
| `backend/main.py` | FastAPI entry: CORS, lifespan, /api/health (Wave 3: + SSE endpoint) | 300 |
| `backend/app/__init__.py` | Empty package init | 1 |
| `backend/app/config.py` | Pydantic Settings: LLM config, max_retries, CORS origins | 100 |
| `backend/app/state.py` | AgentState TypedDict for LangGraph (messages, phase, question, sql, etc.) | 100 |
| `backend/app/models.py` | Pydantic models: QueryRequest, TableInfo, HealthResponse, SchemaResponse | 100 |
| `backend/app/database.py` | SQLite init (4 tables + seed data), get_connection, get_schema_text | 500 |
| `backend/app/agent.py` | StateGraph build + compile (NOT YET CREATED — Wave 2) | — |
| `backend/app/nodes/__init__.py` | Empty package init | 1 |
| `backend/app/nodes/analyze.py` | Question classification node (NOT YET CREATED — Wave 2) | — |
| `backend/app/nodes/generate_sql.py` | SQL generation with retry context (NOT YET CREATED — Wave 2) | — |
| `backend/app/nodes/execute.py` | SQL execution + error capture (NOT YET CREATED — Wave 2) | — |
| `backend/app/nodes/translate.py` | Result → natural language (NOT YET CREATED — Wave 2) | — |
| `backend/app/nodes/chitchat.py` | Chitchat + error fallback (NOT YET CREATED — Wave 2) | — |
| `backend/app/tools/__init__.py` | Empty package init | 1 |
| `backend/app/tools/get_tables.py` | @tool: get table schema (NOT YET CREATED — Wave 2) | — |
| `backend/app/tools/execute_query.py` | @tool: execute read-only query (NOT YET CREATED — Wave 2) | — |

## Frontend

| File | Description | ~Tokens |
|------|-------------|---------|
| `frontend/package.json` | Vite + React + TypeScript + highlight.js deps | 100 |
| `frontend/tsconfig.json` | TypeScript config | 100 |
| `frontend/vite.config.ts` | Vite config with proxy | 50 |
| `frontend/index.html` | Entry HTML | 50 |
| `frontend/src/main.tsx` | React entry | 50 |
| `frontend/src/App.tsx` | App skeleton (NOT YET ASSEMBLED — Wave 3) | 50 |
| `frontend/src/App.css` | Global styles + CSS variables | 300 |
| `frontend/src/vite-env.d.ts` | Vite type declarations | 20 |
| `frontend/src/types/index.ts` | AgentPhase, AgentEvent, QueryState types | 100 |
| `frontend/src/context/QueryContext.tsx` | React Context + Reducer | 150 |
| `frontend/src/services/api.ts` | fetch wrapper for health + SSE query | 100 |
| `frontend/src/hooks/useSSE.ts` | SSE stream parsing hook (NOT YET CREATED — Wave 2) | — |
| `frontend/src/components/QueryInput.tsx/css` | Search input component (NOT YET CREATED — Wave 2) | — |
| `frontend/src/components/StatusBar.tsx/css` | Phase indicator (NOT YET CREATED — Wave 2) | — |
| `frontend/src/components/SqlDisplay.tsx/css` | SQL code block with highlight.js (NOT YET CREATED — Wave 2) | — |
| `frontend/src/components/ResultTable.tsx/css` | Query result table (NOT YET CREATED — Wave 2) | — |
| `frontend/src/components/AnswerCard.tsx/css` | Natural language answer (NOT YET CREATED — Wave 2) | — |
| `frontend/src/components/ErrorDisplay.tsx/css` | Error message display (NOT YET CREATED — Wave 2) | — |

## Docs

| File | Description | ~Tokens |
|------|-------------|---------|
| `docs/backend-development.md` | Full backend design: types, graph, nodes, SSE, API | 3000 |
| `docs/frontend-development.md` | Full frontend design: components, SSE hook, styles | 2500 |
| `nl2sql-agent-requirements.md` | F1-F7 requirements | 300 |
| `CLAUDE.md` | Multi-agent parallel development guide | 1500 |
