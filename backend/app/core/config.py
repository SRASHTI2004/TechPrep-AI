"""Application settings, loaded from environment variables (and `.env` in development).

Every tunable lives here so behaviour can change per environment without code changes.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_DIR = BACKEND_DIR.parent

DEV_JWT_SECRET = "dev-only-insecure-secret-change-me"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Root .env is shared with docker compose; backend/.env can override it locally.
        env_file=(REPO_DIR / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- App ---
    env: Literal["dev", "test", "prod"] = "dev"
    app_name: str = "TechPrep AI"
    log_level: str = "INFO"
    log_json: bool = False
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # --- Database / queue ---
    database_url: str = "postgresql+psycopg://techprep:techprep@localhost:5432/techprep"
    redis_url: str | None = None
    # "celery": hand ingestion to a Celery worker via Redis.
    # "inline": run it in-process after the response (lite mode, no Redis needed).
    ingestion_mode: Literal["celery", "inline"] = "inline"

    # --- Auth ---
    jwt_secret: str = DEV_JWT_SECRET
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # --- Rate limiting ---
    rate_limit_enabled: bool = True
    rate_limit_chat: str = "20/minute"
    rate_limit_upload: str = "10/minute"
    rate_limit_auth: str = "10/minute"

    # --- Uploads ---
    upload_dir: Path = REPO_DIR / "data" / "uploads"
    max_upload_mb: int = 20

    # --- Embeddings / reranking ---
    embedding_provider: Literal["fastembed", "hash"] = "fastembed"
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dim: int = 384
    # Recommended query instruction for bge-*-en-v1.5 retrieval.
    embedding_query_prefix: str = "Represent this sentence for searching relevant passages: "
    model_cache_dir: str | None = None
    reranker_enabled: bool = True
    reranker_model: str = "Xenova/ms-marco-MiniLM-L-6-v2"
    warmup_models: bool = False

    # --- Chunking ---
    chunk_size: int = 1000
    chunk_overlap: int = 150
    min_chunk_chars: int = 80

    # --- Retrieval ---
    retrieval_mode: Literal["hybrid", "vector", "keyword"] = "hybrid"
    retrieval_candidates: int = 20
    top_k: int = 5
    rrf_k: int = 60
    # "I don't know" gate: below these scores, we don't call the LLM.
    rerank_min_score: float = 0.02  # sigmoid of cross-encoder logit
    vector_min_similarity: float = 0.62  # cosine similarity (used when reranker is off)

    # --- LLM ---
    llm_primary: Literal["gemini", "groq", "fake"] = "gemini"
    llm_fallback: Literal["gemini", "groq", "fake", "none"] = "groq"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    groq_api_key: str | None = None
    groq_model: str = "openai/gpt-oss-20b"
    groq_reasoning_effort: str | None = "low"  # gpt-oss models only; None to omit
    llm_temperature: float = 0.1
    llm_max_tokens: int = 1024
    llm_timeout_seconds: float = 60.0
    query_rewrite_enabled: bool = True
    history_turns: int = 4

    # --- Evaluation (offline only) ---
    eval_judge_provider: Literal["gemini", "groq", "fake"] = "groq"
    eval_judge_model: str = "openai/gpt-oss-120b"

    first_admin_email: str | None = Field(
        default=None, description="If set, this email is given the admin role on registration."
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @model_validator(mode="after")
    def _check_production_safety(self) -> "Settings":
        if self.env == "prod" and self.jwt_secret == DEV_JWT_SECRET:
            raise ValueError("JWT_SECRET must be set to a strong random value when ENV=prod")
        if self.ingestion_mode == "celery" and not self.redis_url:
            raise ValueError("INGESTION_MODE=celery requires REDIS_URL")
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("CHUNK_OVERLAP must be smaller than CHUNK_SIZE")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
