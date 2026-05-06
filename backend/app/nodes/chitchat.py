from langchain_openai import ChatOpenAI

from app.config import settings
from app.state import AgentState

chitchat_llm = ChatOpenAI(
    model=settings.llm_model,
    api_key=settings.llm_api_key,
    base_url=settings.llm_base_url,
    temperature=0.3,
    timeout=30,
    max_retries=2,
)


def run_chitchat(state: AgentState) -> dict:
    question = state["question"]

    prompt = (
        "你是一个NL2SQL助手，主要功能是将自然语言问题转换为SQL查询并返回数据库查询结果。"
        "对于用户的闲聊问题，请友好地回复，并提示用户可以尝试询问数据库相关的问题。\n\n"
        f"用户：{question}\n助手："
    )

    response = chitchat_llm.invoke(prompt)

    return {"phase": "done", "answer": response.content.strip()}


def run_error(state: AgentState) -> dict:
    error = state.get("error", "未知错误")
    retry_count = state.get("retry_count", 0)

    answer = (
        f"抱歉，查询失败了。已重试 {retry_count} 次。\n"
        f"错误信息：{error}\n"
        "请尝试换一种问法。"
    )

    return {"phase": "error", "answer": answer}
