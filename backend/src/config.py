from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Google Cloud settings (uses Application Default Credentials)
    google_cloud_project: str
    google_cloud_location: str = "us-central1"

    # Vertex AI RAG settings
    vertex_ai_corpus_name: str = "temporal-context-corpus"
    # RAG corpus resource name (saved after creation for fast loading)
    # Format: projects/{PROJECT_ID}/locations/{LOCATION}/ragCorpora/{CORPUS_ID}
    rag_corpus_resource_name: Optional[str] = None

    # Vector Search backend (required for RAG Engine)
    # Format: projects/{PROJECT_NUMBER}/locations/{LOCATION}/indexes/{INDEX_ID}
    vector_search_index: Optional[str] = None
    # Format: projects/{PROJECT_NUMBER}/locations/{LOCATION}/indexEndpoints/{ENDPOINT_ID}
    vector_search_index_endpoint: Optional[str] = None

    gcs_bucket_name: Optional[str] = None
    embedding_model_name: str = "text-embedding-005"  # Options: text-embedding-005 (latest), text-embedding-004, text-multilingual-embedding-002
    embedding_requests_per_minute: int = 60  # Rate limit for embedding API calls
    index_algorithm: str = "brute_force"  # Options: brute_force (fast deploy), tree_ah (production scale)

    # Query settings
    default_top_k: int = 20  # Default number of results to return for queries (controlled by system, not LLM)

    # FastAPI settings
    api_title: str = "Temporal Context RAG Agent"
    api_version: str = "1.0.0"

    # Logging settings
    log_format: str = "logfmt"  # Options: "json" or "logfmt"
    log_level: str = "INFO"  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
    log_colors: bool = True  # Enable colored output for logfmt format

    class Config:
        env_file = "../.env"
        case_sensitive = False


settings = Settings()
