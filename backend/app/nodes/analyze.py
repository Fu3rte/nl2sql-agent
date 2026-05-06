from langchain_openai import ChatOpenAI

from app.config import settings
from app.state import AgentState

analyze_llm = ChatOpenAI(
    model=settings.llm_model,
    api_key=settings.llm_api_key,
    base_url=settings.llm_base_url,
    temperature=0.0,
    timeout=30,
    max_retries=2,
)


def run(state: AgentState) -> dict:
    question = state["question"]

    prompt = f"""判断以下问题是否需要查询数据库。仅回答 YES 或 NO。

分类标准：
- YES: 需要查询数据库的问题（数据统计、排行、筛选、聚合、销售分析、库存等）
- NO: 不需要数据库查询的问题（问候、闲聊、常识、自我介绍等）

用户问题：{question}

回答："""

    response = analyze_llm.invoke(prompt)
    answer = response.content.strip().upper()
    is_data_query = answer.startswith("YES")

    return {"phase": "analyzing", "is_data_query": is_data_query}
