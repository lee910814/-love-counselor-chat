from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # API Keys
    anthropic_api_key: str = ""
    huggingface_api_key: str = ""

    # Qdrant
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection_name: str = "love_counselor"

    # Embedding
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

    # Server
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    class Config:
        env_file = "../.env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
