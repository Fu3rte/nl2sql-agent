from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class AgentState(TypedDict):
    """LangGraph shared state flowing through all nodes."""

    messages: Annotated[list[BaseMessage], add_messages]
    phase: str
    question: str
    is_data_query: bool
    sql: str | None
    columns: list[str] | None
    rows: list[dict] | None
    answer: str | None
    error: str | None
    retry_count: int
