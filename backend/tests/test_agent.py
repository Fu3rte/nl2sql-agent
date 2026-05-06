"""Test LangGraph agent: compilation, routing, and full pipeline."""

import pytest
from app.agent import build_graph, route_after_analyze, route_after_execute


class TestGraphCompilation:
    def test_build_graph_returns_compiled(self):
        graph = build_graph()
        assert graph is not None
        node_names = list(graph.nodes.keys())
        assert "analyze_question" in node_names
        assert "generate_sql" in node_names
        assert "execute_sql" in node_names
        assert "translate_result" in node_names
        assert "generate_chitchat_answer" in node_names
        assert "error_response" in node_names

    def test_graph_has_start_node(self):
        graph = build_graph()
        assert "__start__" in graph.nodes


class TestRouteAfterAnalyze:
    def test_data_query_goes_to_generate_sql(self):
        assert route_after_analyze({"is_data_query": True}) == "generate_sql"

    def test_chitchat_goes_to_chitchat(self):
        assert route_after_analyze({"is_data_query": False}) == "generate_chitchat_answer"


class TestRouteAfterExecute:
    def test_success_goes_to_translate(self):
        assert route_after_execute({"error": None, "retry_count": 0}) == "translate_result"

    def test_retry_below_limit_goes_to_generate_sql(self):
        assert (
            route_after_execute({"error": "some error", "retry_count": 1})
            == "generate_sql"
        )
        assert (
            route_after_execute({"error": "some error", "retry_count": 2})
            == "generate_sql"
        )

    def test_retry_at_limit_goes_to_error(self):
        assert (
            route_after_execute({"error": "some error", "retry_count": 3})
            == "error_response"
        )
        assert (
            route_after_execute({"error": "some error", "retry_count": 4})
            == "error_response"
        )


@pytest.mark.asyncio
class TestFullPipeline:
    async def test_data_query_full_flow(self):
        """A real data query should go through analyze → generate → execute → translate."""
        from app.agent import agent_graph

        initial_state = {
            "question": "How many customers are there?",
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

        phases = []
        async for state in agent_graph.astream(initial_state, stream_mode="values"):
            if isinstance(state, dict) and state.get("phase"):
                phases.append(state["phase"])

        assert "analyzing" in phases
        assert "generating" in phases
        assert "executing" in phases
        assert "done" in phases  # successful completion

    async def test_chitchat_full_flow(self):
        """A chitchat question should go analyze → chitchat without SQL generation."""
        from app.agent import agent_graph

        initial_state = {
            "question": "Hi, how are you?",
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

        phases = []
        is_chitchat_values = []
        async for state in agent_graph.astream(initial_state, stream_mode="values"):
            if isinstance(state, dict) and state.get("phase"):
                phases.append(state["phase"])
                is_chitchat_values.append(state.get("is_data_query") is False)

        assert "analyzing" in phases
        assert "done" in phases
        # No SQL execution for chitchat
        assert "generating" not in phases
        assert "executing" not in phases
