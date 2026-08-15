"""
Every other file reads configuration from `settings` (this module) instead
of calling os.environ directly - one place to change, one place to audit.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # LLM + embeddings (Google GenAI SDK)
    google_api_key: str = ""
    llm_model: str = "gemini-2.0-flash"
    embedding_model: str = "text-embedding-004"

    # Local storage - no external DB servers, no Docker
    sqlite_path: str = "./app/data/scholaragent.db"
    chroma_path: str = "./app/data/chroma_store"
    chroma_collection: str = "scholaragent_papers"

    # Web search
    tavily_api_key: str = ""

    # App
    app_env: str = "development"
    cors_origins: str = "http://localhost:5173"

    # Evaluation
    eval_top_k: int = 5

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
