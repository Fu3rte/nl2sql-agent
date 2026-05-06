from langchain_openai import ChatOpenAI

from app.config import settings
from app.state import AgentState

translate_llm = ChatOpenAI(
    model=settings.llm_model,
    api_key=settings.llm_api_key,
    base_url=settings.llm_base_url,
    temperature=0.3,
    timeout=30,
    max_retries=2,
)


def run(state: AgentState) -> dict:
    question = state["question"]
    sql = state.get("sql", "")
    rows = state.get("rows") or []
    columns = state.get("columns") or []

    display_rows = rows[:20]

    if not rows:
        answer = "查询执行成功，但没有找到匹配的数据。"
        return {"phase": "done", "answer": answer}

    prompt = (
        f"用户问题：{question}\n"
        f"执行SQL：{sql}\n"
        f"查询结果（共{len(rows)}行，以下显示前{len(display_rows)}行）：\n"
        f"列：{columns}\n"
        f"数据：{display_rows}\n\n"
        "请用自然语言简洁地回答用户的问题。如果结果很多，请总结关键发现。"
    )

    response = translate_llm.invoke(prompt)

    return {"phase": "done", "answer": response.content.strip()}
