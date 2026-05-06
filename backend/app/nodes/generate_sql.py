import re

from langchain_openai import ChatOpenAI

from app.config import settings
from app.state import AgentState
from app.database import get_schema_text

generate_llm = ChatOpenAI(
    model=settings.llm_model,
    api_key=settings.llm_api_key,
    base_url=settings.llm_base_url,
    temperature=0.0,
    timeout=30,
    max_retries=2,
)


def run(state: AgentState) -> dict:
    question = state["question"]
    error = state.get("error")
    previous_sql = state.get("sql")
    retry_count = state.get("retry_count", 0)
    schema = get_schema_text()

    system_prompt = f"""你是一个SQLite数据库专家。以下是数据库的表结构：

{schema}

请根据用户的自然语言问题生成SQLite查询语句。只输出SQL语句，不要有任何解释。

SQLite注意事项：
- 使用标准的SQLite语法
- 日期函数使用 date('now') 格式
- 聚合查询需要 GROUP BY
- 字符串使用单引号
- 不要使用 MySQL 或 PostgreSQL 特有的函数"""

    if error and previous_sql:
        user_prompt = (
            f"问题：{question}\n\n"
            f"上次生成的SQL：\n{previous_sql}\n\n"
            f"执行时发生了以下错误：\n{error}\n\n"
            "请修正SQL语句并重新生成。只输出SQL语句。"
        )
    else:
        user_prompt = f"问题：{question}\n\nSQL："

    response = generate_llm.invoke([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ])

    sql = _extract_sql(response.content)
    phase = "retrying" if retry_count > 0 else "generating"

    return {"phase": phase, "sql": sql}


def _extract_sql(text: str) -> str:
    """Extract SQL from LLM output, handling markdown code blocks."""
    text = text.strip()
    pattern = r"```(?:sql)?\s*\n?(.*?)```"
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return text
