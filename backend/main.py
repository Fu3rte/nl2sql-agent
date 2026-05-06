from contextlib import asynccontextmanager
import json
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.config import settings
from app.database import init_db, get_schema_info
from app.agent import agent_graph
from app.models import HealthResponse, QueryRequest, SchemaResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
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
    return SchemaResponse(tables=get_schema_info())


@app.post("/api/query")
async def query(request: QueryRequest):
    async def event_stream():
        initial_state = {
            "question": request.question,
            "messages": [],
            "is_data_query": False,
            "sql": None,
            "columns": None,
            "rows": None,
            "answer": None,
            "error": None,
            "retry_count": 0,
            "phase": "",
        }
        try:
            async for state in agent_graph.astream(initial_state, stream_mode="values"):
                if isinstance(state, dict) and state.get("phase"):
                    payload = _build_sse_payload(state)
                    yield f"event: phase\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
        except Exception as exc:
            logger.exception("SSE stream error")
            payload = _build_sse_payload({
                "phase": "error",
                "error": str(exc),
                "question": request.question,
                "retry_count": 0,
            })
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
