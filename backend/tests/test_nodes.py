"""Test individual node functions."""

import pytest
from app.nodes.analyze import run as analyze_run
from app.nodes.generate_sql import run as gen_sql_run, _extract_sql
from app.nodes.execute import run as exec_run
from app.nodes.translate import run as translate_run
from app.nodes.chitchat import run_chitchat, run_error


def _base_state(**overrides):
    """Build a minimal AgentState dict for node testing."""
    s = {
        "question": "test question",
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
    s.update(overrides)
    return s


class TestAnalyzeNode:
    def test_returns_analyzing_phase(self):
        result = analyze_run(_base_state(question="How many orders?"))
        assert result["phase"] == "analyzing"

    def test_data_query_detected(self):
        result = analyze_run(_base_state(question="What is the total sales?"))
        assert "is_data_query" in result

    def test_chitchat_detected(self):
        result = analyze_run(_base_state(question="Hello, how are you?"))
        assert result["is_data_query"] is False


class TestGenerateSqlNode:
    def test_returns_generating_phase(self):
        state = _base_state(question="How many customers?", is_data_query=True)
        result = gen_sql_run(state)
        assert result["phase"] == "generating"

    def test_retry_sets_retrying_phase(self):
        state = _base_state(
            question="How many customers?",
            is_data_query=True,
            error="no such table: x",
            sql="SELECT * FROM x",
            retry_count=1,
        )
        result = gen_sql_run(state)
        assert result["phase"] == "retrying"

    def test_returns_sql(self):
        state = _base_state(question="How many orders?", is_data_query=True)
        result = gen_sql_run(state)
        assert result["sql"] is not None
        assert len(result["sql"]) > 0


class TestExtractSql:
    def test_extracts_markdown_sql_block(self):
        text = "Here is:\n```sql\nSELECT * FROM orders;\n```"
        assert _extract_sql(text) == "SELECT * FROM orders;"

    def test_extracts_markdown_block_no_lang(self):
        text = "```\nSELECT 1\n```"
        assert _extract_sql(text) == "SELECT 1"

    def test_returns_plain_text_fallback(self):
        assert _extract_sql("SELECT 1") == "SELECT 1"

    def test_trims_whitespace(self):
        assert _extract_sql("  SELECT 1  ") == "SELECT 1"


class TestExecuteNode:
    def test_executes_valid_select(self):
        state = _base_state(sql="SELECT COUNT(*) FROM customers")
        result = exec_run(state)
        assert result["phase"] == "executing"
        assert result["error"] is None
        assert result["columns"] == ["COUNT(*)"]
        assert result["rows"][0]["COUNT(*)"] == 20

    def test_rejects_write_statement(self):
        state = _base_state(sql="DELETE FROM customers")
        result = exec_run(state)
        assert result["error"] is not None
        assert "仅支持SELECT" in result["error"]
        assert result["retry_count"] == 1

    def test_increments_retry_on_error(self):
        state = _base_state(sql="SELECT * FROM nonexistent_table", retry_count=0)
        result = exec_run(state)
        assert result["retry_count"] == 1
        assert result["error"] is not None

    def test_handles_no_sql(self):
        state = _base_state(sql=None)
        result = exec_run(state)
        assert result["error"] is not None
        assert "未生成有效" in result["error"]
        assert result["retry_count"] == 1


class TestTranslateNode:
    def test_returns_done_phase(self):
        state = _base_state(
            question="How many customers?",
            sql="SELECT COUNT(*) FROM customers",
            columns=["COUNT(*)"],
            rows=[{"COUNT(*)": 20}],
        )
        result = translate_run(state)
        assert result["phase"] == "done"
        assert result["answer"] is not None

    def test_empty_rows_returns_no_data_message(self):
        state = _base_state(
            question="Find nobody",
            sql="SELECT * FROM customers WHERE 1=0",
            columns=["id", "name"],
            rows=[],
        )
        result = translate_run(state)
        assert result["phase"] == "done"
        assert "没有找到" in result["answer"] or "no matching" in result["answer"].lower()


class TestChitchatNode:
    def test_returns_done_phase(self):
        state = _base_state(question="Hello!")
        result = run_chitchat(state)
        assert result["phase"] == "done"
        assert result["answer"] is not None


class TestErrorNode:
    def test_returns_error_phase(self):
        state = _base_state(error="something went wrong", retry_count=3)
        result = run_error(state)
        assert result["phase"] == "error"
        assert "something went wrong" in result["answer"]
        assert "3" in result["answer"]
