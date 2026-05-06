import sqlite3

from app.state import AgentState
from app.database import get_connection


def run(state: AgentState) -> dict:
    sql = state.get("sql")
    retry_count = state.get("retry_count", 0)

    if not sql:
        return {
            "phase": "executing",
            "error": "未生成有效的SQL语句",
            "retry_count": retry_count + 1,
        }

    if not _is_read_only(sql):
        return {
            "phase": "executing",
            "error": "仅支持SELECT查询，不允许修改数据",
            "retry_count": retry_count + 1,
        }

    try:
        conn = get_connection()
        cursor = conn.execute(sql)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        conn.close()

        return {
            "phase": "executing",
            "columns": columns,
            "rows": [dict(row) for row in rows],
            "error": None,
        }
    except sqlite3.Error as e:
        return {
            "phase": "executing",
            "error": str(e),
            "retry_count": retry_count + 1,
        }


def _is_read_only(sql: str) -> bool:
    stripped = sql.strip().upper()
    return stripped.startswith("SELECT") or stripped.startswith("WITH")
