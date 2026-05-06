# Cerebrum — NL2SQL Agent

## Key Learnings

- DeepSeek API uses OpenAI-compatible endpoint at `https://api.deepseek.com/v1` with model `deepseek-chat`
- LangGraph `astream_events(version="v2")` provides per-node events; each `on_chain_end` with output containing `phase` gets pushed as SSE
- SQLite with `row_factory = sqlite3.Row` enables dict-style column access
- Schema injection via system prompt (not Tool Calling) is more reliable for simple single-query scenarios

## User Preferences

- No emojis unless explicitly requested
- Concise responses, no trailing summaries
- Only commit after Wave completion and verification (not mid-Wave)

## Do-Not-Repeat

- (2026-05-06) Don't commit `.claude/settings.local.json` — it contains local user settings
- (2026-05-06) Filter `sqlite_%` system tables from `get_schema_text()` output — they're noise for LLM prompts

## Decision Log

- (2026-05-06) **Schema injection method**: Chose system prompt embedding over Tool Calling for SQL generation — simpler, more reliable for single-query scenarios, avoids tool calling uncertainty
- (2026-05-06) **Database choice**: SQLite with auto-generated seed data on first startup — zero config requirement for users
- (2026-05-06) **State management**: React Context + useReducer instead of Redux/Zustand — minimal deps for a single-page app
