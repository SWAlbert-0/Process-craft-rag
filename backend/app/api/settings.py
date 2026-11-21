import time
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from app.config import Settings, get_settings
from app.errors import AppError
from app.services.domain import Candidate, SearchHit
from app.services.embeddings import EmbeddingClient, ModelServiceError
from app.services.llm import LLMClient
from app.services.rerank import RerankClient
from app.services.runtime_settings import (
    public_settings,
    reset_runtime_settings,
    save_runtime_settings,
)

router = APIRouter(prefix="/settings", tags=["settings"])


class SettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    llm_provider: str | None = Field(default=None, max_length=40)
    llm_base_url: str | None = Field(default=None, max_length=500)
    llm_model: str | None = Field(default=None, max_length=200)
    llm_api_key: str | None = Field(default=None, max_length=1000)
    clear_llm_api_key: bool = False
    llm_timeout_seconds: float | None = Field(default=None, gt=0, le=300)
    model_max_retries: int | None = Field(default=None, ge=0, le=4)
    llm_max_output_tokens: int | None = Field(default=None, ge=1024, le=32000)
    embedding_provider: str | None = Field(default=None, max_length=40)
    embedding_model: str | None = Field(default=None, max_length=200)
    embedding_dimensions: int | None = Field(default=None, ge=128, le=4096)
    embedding_batch_size: int | None = Field(default=None, ge=1, le=10)
    dashscope_api_key: str | None = Field(default=None, max_length=1000)
    clear_dashscope_api_key: bool = False
    dashscope_workspace_id: str | None = Field(default=None, max_length=200)
    clear_dashscope_workspace_id: bool = False
    dashscope_region: str | None = Field(default=None, max_length=40)
    rerank_provider: str | None = Field(default=None, max_length=40)
    rerank_model: str | None = Field(default=None, max_length=200)
    chunk_target_chars: int | None = Field(default=None, ge=128, le=4000)
    chunk_overlap_chars: int | None = Field(default=None, ge=0, le=1000)
    chunk_min_chars: int | None = Field(default=None, ge=16, le=1000)
    dense_top_k: int | None = Field(default=None, ge=1, le=100)
    sparse_top_k: int | None = Field(default=None, ge=1, le=100)
    rrf_k: int | None = Field(default=None, ge=1, le=200)
    fusion_top_n: int | None = Field(default=None, ge=1, le=100)
    rerank_top_n: int | None = Field(default=None, ge=1, le=30)
    context_token_budget: int | None = Field(default=None, ge=500, le=20000)
    rerank_min_score: float | None = Field(default=None, ge=0, le=1)


class ConnectionTest(BaseModel):
    service: Literal["llm", "embedding", "rerank"]


def validated_changes(settings: Settings, payload: SettingsUpdate) -> dict:
    changes = payload.model_dump(exclude_unset=True)
    merged = public_settings(settings)
    merged.update({key: value for key, value in changes.items() if value is not None})
    if not merged["llm_base_url"].startswith(("http://", "https://")):
        raise AppError(422, "VALIDATION_ERROR", "LLM Base URL 必须使用 HTTP 或 HTTPS")
    if merged["chunk_target_chars"] <= merged["chunk_overlap_chars"]:
        raise AppError(422, "VALIDATION_ERROR", "分块目标长度必须大于重叠长度")
    if merged["chunk_min_chars"] > merged["chunk_target_chars"]:
        raise AppError(422, "VALIDATION_ERROR", "最小分块长度不能超过目标长度")
    if merged["rerank_top_n"] > merged["fusion_top_n"]:
        raise AppError(422, "VALIDATION_ERROR", "重排数量不能超过融合候选数量")
    return changes


@router.get("")
def read_settings(settings: Settings = Depends(get_settings)) -> dict:
    return public_settings(settings)


@router.put("")
def update_settings(payload: SettingsUpdate, settings: Settings = Depends(get_settings)) -> dict:
    changes = validated_changes(settings, payload)
    updated = save_runtime_settings(settings, changes)
    return public_settings(updated)


@router.delete("")
def delete_runtime_settings(settings: Settings = Depends(get_settings)) -> dict:
    return public_settings(reset_runtime_settings(settings))


@router.post("/test")
async def test_connection(
    payload: ConnectionTest, settings: Settings = Depends(get_settings)
) -> dict:
    started = time.perf_counter()
    usage: dict = {}
    try:
        if payload.service == "llm":
            client = LLMClient(settings)
            try:
                _result, usage = await client.complete_json(
                    '只输出 JSON 对象 {"ok":true}。',
                    "执行连接测试，不要添加其他内容。",
                )
            finally:
                await client.close()
        elif payload.service == "embedding":
            client = EmbeddingClient(settings)
            try:
                vectors = await client.embed(["Process Craft connection test"])
                if not vectors:
                    raise ModelServiceError("嵌入服务未返回向量")
            finally:
                await client.close()
        else:
            client = RerankClient(settings)
            try:
                candidates = [
                    Candidate(
                        hit=SearchHit(
                            "test-a",
                            "test",
                            "test",
                            "Machine tool calibration checks spindle accuracy.",
                            1,
                            1,
                            [],
                            0,
                        )
                    ),
                    Candidate(
                        hit=SearchHit(
                            "test-b", "test", "test", "Unrelated cooking recipe.", 1, 1, [], 0
                        )
                    ),
                ]
                ranked = await client.rerank("machine tool calibration", candidates, 2)
                if not ranked:
                    raise ModelServiceError("重排序服务未返回结果")
            finally:
                await client.close()
    except ModelServiceError as exc:
        raise AppError(502, "MODEL_UNAVAILABLE", str(exc)) from exc
    return {
        "service": payload.service,
        "status": "connected",
        "latency_ms": round((time.perf_counter() - started) * 1000, 2),
        "usage": usage,
    }
