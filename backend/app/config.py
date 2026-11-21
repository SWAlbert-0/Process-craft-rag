import json
from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

RUNTIME_PUBLIC_FIELDS = frozenset(
    {
        "llm_provider",
        "llm_base_url",
        "llm_model",
        "llm_timeout_seconds",
        "model_max_retries",
        "llm_max_output_tokens",
        "embedding_provider",
        "embedding_model",
        "embedding_dimensions",
        "embedding_batch_size",
        "rerank_provider",
        "rerank_model",
        "dashscope_region",
        "chunk_target_chars",
        "chunk_overlap_chars",
        "chunk_min_chars",
        "dense_top_k",
        "sparse_top_k",
        "rrf_k",
        "fusion_top_n",
        "rerank_top_n",
        "context_token_budget",
        "rerank_min_score",
    }
)
RUNTIME_SECRET_FIELDS = frozenset({"llm_api_key", "dashscope_api_key", "dashscope_workspace_id"})


def runtime_settings_path(data_dir: Path) -> Path:
    return data_dir / "config" / "runtime-settings.json"


def read_runtime_settings(data_dir: Path) -> dict:
    path = runtime_settings_path(data_dir)
    if not path.exists():
        return {"version": 1, "values": {}, "secrets": {}}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RuntimeError("服务端运行时设置无法读取，请修复或重置本地设置") from exc
    if payload.get("version") != 1:
        raise RuntimeError("服务端运行时设置版本不兼容")
    return payload


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env", "backend/.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        validate_assignment=True,
    )

    app_env: str = "development"
    data_dir: Path = Path("./data")
    backup_dir: Path = Path("./backups")
    log_dir: Path = Path("./logs")
    database_url: str | None = None
    qdrant_url: str = "http://localhost:6333"
    cors_origins: str = "http://localhost:5173"
    max_upload_mb: int = 50
    max_pdf_pages: int = 400

    llm_provider: str = "deepseek"
    llm_base_url: str = "https://api.deepseek.com"
    llm_model: str = "deepseek-flash"
    llm_api_key: SecretStr = SecretStr("")
    llm_timeout_seconds: float = 90
    model_max_retries: int = Field(default=2, ge=0, le=4)
    llm_max_output_tokens: int = 8000

    embedding_provider: str = "dashscope"
    embedding_model: str = "text-embedding-v4"
    embedding_dimensions: int = 1024
    embedding_batch_size: int = Field(default=10, le=10)

    rerank_provider: str = "dashscope"
    rerank_model: str = "qwen3-rerank"
    dashscope_workspace_id: str = ""
    dashscope_region: str = "cn-beijing"
    dashscope_api_key: SecretStr = SecretStr("")

    parser_version: str = "pymupdf-pages-v1"
    chunking_version: str = "paragraph-recursive-v1"
    chunk_target_chars: int = 900
    chunk_overlap_chars: int = 120
    chunk_min_chars: int = 120
    dense_top_k: int = 20
    sparse_top_k: int = 20
    rrf_k: int = 60
    fusion_top_n: int = 30
    rerank_top_n: int = 8
    context_token_budget: int = 5000
    rerank_min_score: float = 0.0

    def __init__(self, **values) -> None:
        super().__init__(**values)
        runtime = read_runtime_settings(self.data_dir)
        for key, value in runtime.get("values", {}).items():
            if key in RUNTIME_PUBLIC_FIELDS:
                setattr(self, key, value)
        for key, value in runtime.get("secrets", {}).items():
            if key in RUNTIME_SECRET_FIELDS:
                setattr(self, key, value)

    @property
    def sqlalchemy_url(self) -> str:
        if self.database_url:
            return self.database_url
        path = self.data_dir.resolve() / "db" / "process_craft.db"
        return f"sqlite:///{path.as_posix()}"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def dashscope_host(self) -> str:
        if self.dashscope_region == "cn-beijing":
            return "https://dashscope.aliyuncs.com"
        return "https://dashscope-intl.aliyuncs.com"

    @property
    def embedding_base_url(self) -> str:
        return f"{self.dashscope_host}/compatible-mode/v1"

    @property
    def rerank_url(self) -> str:
        return f"{self.dashscope_host}/api/v1/services/rerank/text-rerank/text-rerank"

    def ensure_directories(self) -> None:
        for path in (
            self.data_dir / "db",
            self.data_dir / "config",
            self.data_dir / "documents",
            self.data_dir / "parsed",
            self.data_dir / "indexes" / "bm25",
            self.data_dir / "evaluation",
            self.data_dir / "tmp",
            self.backup_dir,
            self.log_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_directories()
    return settings
