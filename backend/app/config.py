from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    # LLM
    llm_api_key: str = ""
    llm_model: str = "deepseek-v4-flash"
    llm_base_url: str = "https://api.deepseek.com"
    llm_temperature: float = 0.0

    # Agent
    max_retries: int = 3

    # CORS
    cors_origins: list[str] = ["http://localhost:5173"]


settings = Settings()
