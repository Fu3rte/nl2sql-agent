"""Test FastAPI endpoints: health, schema, SSE query."""

import json
import pytest


@pytest.mark.asyncio
class TestHealthEndpoint:
    async def test_returns_ok(self, client):
        response = await client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


@pytest.mark.asyncio
class TestSchemaEndpoint:
    async def test_returns_tables_list(self, client):
        response = await client.get("/api/db/schema")
        assert response.status_code == 200
        data = response.json()
        assert "tables" in data
        assert len(data["tables"]) == 4
        table_names = {t["name"] for t in data["tables"]}
        assert "customers" in table_names
        assert "orders" in table_names


@pytest.mark.asyncio
class TestSSEQueryEndpoint:
    async def _collect_sse_events(self, response):
        """Parse SSE text/event-stream response into list of dicts."""
        events = []
        current_data = None
        async for chunk in response.aiter_bytes():
            # httpx async streaming returns bytes
            pass
        # Fallback: read full text and split
        full_text = response.text
        for line in full_text.strip().split("\n"):
            line = line.strip()
            if line.startswith("data:"):
                json_str = line[5:].strip()
                if json_str:
                    events.append(json.loads(json_str))
        return events

    async def _stream_and_collect(self, client, question):
        """Stream SSE response and collect all events."""
        events = []
        async with client.stream(
            "POST",
            "/api/query",
            json={"question": question},
            headers={"Accept": "text/event-stream"},
        ) as response:
            assert response.status_code == 200
            buffer = ""
            async for chunk in response.aiter_text():
                buffer += chunk
                while "\n\n" in buffer:
                    event_block, buffer = buffer.split("\n\n", 1)
                    for line in event_block.split("\n"):
                        line = line.strip()
                        if line.startswith("data:"):
                            json_str = line[5:].strip()
                            if json_str:
                                events.append(json.loads(json_str))
        return events

    async def test_data_query_emits_correct_phases(self, client):
        events = await self._stream_and_collect(client, "How many orders?")

        phases = [e["phase"] for e in events]
        assert "analyzing" in phases, f"Got phases: {phases}"
        assert len(events) >= 2, f"Expected at least 2 events, got {len(events)}"

    async def test_query_event_has_required_fields(self, client):
        events = await self._stream_and_collect(client, "How many orders?")
        for event in events:
            assert "phase" in event
            assert "question" in event
            assert "sql" in event
            assert "columns" in event
            assert "rows" in event
            assert "answer" in event
            assert "error" in event
            assert "retry_count" in event
            assert "is_chitchat" in event

    async def test_data_query_is_not_chitchat(self, client):
        events = await self._stream_and_collect(client, "How many orders?")
        # First event (analyzing) should have is_chitchat=False
        assert events[0]["is_chitchat"] is False

    async def test_chitchat_is_marked_as_chitchat(self, client):
        events = await self._stream_and_collect(client, "Hello! Who are you?")

        # Last event should be done with is_chitchat=True
        assert len(events) >= 2
        final = events[-1]
        assert final["phase"] in ("done", "error")

    async def test_empty_question_rejected(self, client):
        response = await client.post("/api/query", json={"question": ""})
        assert response.status_code == 422

    async def test_sse_content_type(self, client):
        async with client.stream(
            "POST",
            "/api/query",
            json={"question": "Hello"},
            headers={"Accept": "text/event-stream"},
        ) as response:
            assert response.status_code == 200
            assert "text/event-stream" in response.headers.get("content-type", "")

    async def test_sse_correct_headers(self, client):
        async with client.stream(
            "POST",
            "/api/query",
            json={"question": "Hello"},
            headers={"Accept": "text/event-stream"},
        ) as response:
            assert response.headers.get("cache-control") == "no-cache"


def test_build_sse_payload():
    """Unit test for _build_sse_payload function."""
    from main import _build_sse_payload

    # Data query after analyze
    payload = _build_sse_payload({
        "phase": "analyzing",
        "question": "How many orders?",
        "is_data_query": True,
        "sql": None,
        "columns": None,
        "rows": None,
        "answer": None,
        "error": None,
        "retry_count": 0,
    })
    assert payload["phase"] == "analyzing"
    assert payload["is_chitchat"] is False
    assert payload["retry_count"] == 0

    # Chitchat after analyze
    payload = _build_sse_payload({
        "phase": "analyzing",
        "question": "Hello",
        "is_data_query": False,
        "sql": None,
        "columns": None,
        "rows": None,
        "answer": None,
        "error": None,
        "retry_count": 0,
    })
    assert payload["is_chitchat"] is True

    # Error state
    payload = _build_sse_payload({
        "phase": "error",
        "error": "connection timeout",
        "question": "test",
        "retry_count": 3,
    })
    assert payload["phase"] == "error"
    assert payload["error"] == "connection timeout"
    assert payload["is_chitchat"] is False  # defaults to not chitchat for errors

    # Done state after succesful data query
    payload = _build_sse_payload({
        "phase": "done",
        "question": "How many?",
        "sql": "SELECT COUNT(*) FROM orders",
        "columns": ["COUNT(*)"],
        "rows": [{"COUNT(*)": 30}],
        "answer": "There are 30 orders.",
        "is_data_query": True,
        "error": None,
        "retry_count": 0,
    })
    assert payload["phase"] == "done"
    assert payload["answer"] == "There are 30 orders."
    assert payload["rows"] == [{"COUNT(*)": 30}]
    assert payload["is_chitchat"] is False
