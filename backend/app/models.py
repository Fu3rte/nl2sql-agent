from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, description="User's natural language question")


class TableInfo(BaseModel):
    name: str
    columns: list[dict]  # [{"name": "id", "type": "INTEGER"}, ...]


class HealthResponse(BaseModel):
    status: str
    db_loaded: bool


class SchemaResponse(BaseModel):
    tables: list[TableInfo]
