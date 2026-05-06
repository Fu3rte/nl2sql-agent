from langgraph.graph import StateGraph, START, END

from app.config import settings
from app.state import AgentState
from app.nodes import analyze, generate_sql, execute, translate, chitchat


def route_after_analyze(state: AgentState) -> str:
    if state["is_data_query"]:
        return "generate_sql"
    return "generate_chitchat_answer"


def route_after_execute(state: AgentState) -> str:
    if state["error"] is None:
        return "translate_result"
    if state["retry_count"] < settings.max_retries:
        return "generate_sql"
    return "error_response"


def build_graph() -> StateGraph:
    builder = StateGraph(AgentState)

    builder.add_node("analyze_question", analyze.run)
    builder.add_node("generate_chitchat_answer", chitchat.run_chitchat)
    builder.add_node("generate_sql", generate_sql.run)
    builder.add_node("execute_sql", execute.run)
    builder.add_node("translate_result", translate.run)
    builder.add_node("error_response", chitchat.run_error)

    builder.add_edge(START, "analyze_question")

    builder.add_conditional_edges(
        "analyze_question",
        route_after_analyze,
        {
            "generate_sql": "generate_sql",
            "generate_chitchat_answer": "generate_chitchat_answer",
        },
    )
    builder.add_edge("generate_sql", "execute_sql")
    builder.add_conditional_edges(
        "execute_sql",
        route_after_execute,
        {
            "translate_result": "translate_result",
            "generate_sql": "generate_sql",
            "error_response": "error_response",
        },
    )

    builder.add_edge("generate_chitchat_answer", END)
    builder.add_edge("translate_result", END)
    builder.add_edge("error_response", END)

    return builder.compile()


agent_graph = build_graph()
