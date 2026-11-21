import math

import httpx

from app.config import Settings


class ModelServiceError(RuntimeError):
    pass


class EmbeddingClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        key = settings.dashscope_api_key.get_secret_value()
        if not key:
            raise ModelServiceError("尚未配置嵌入服务密钥")
        headers = {"Authorization": f"Bearer {key}"}
        if settings.dashscope_workspace_id:
            headers["X-DashScope-WorkSpace"] = settings.dashscope_workspace_id
        self.client = httpx.AsyncClient(
            base_url=settings.embedding_base_url,
            headers=headers,
            timeout=settings.llm_timeout_seconds,
        )

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self.settings.embedding_batch_size):
            batch = texts[start : start + self.settings.embedding_batch_size]
            payload = {
                "model": self.settings.embedding_model,
                "input": batch,
                "dimensions": self.settings.embedding_dimensions,
                "encoding_format": "float",
            }
            data = await self._post("/embeddings", payload)
            rows = sorted(data.get("data", []), key=lambda row: row.get("index", 0))
            if len(rows) != len(batch):
                raise ModelServiceError("嵌入服务返回数量不完整")
            for row in rows:
                vector = row.get("embedding", [])
                if len(vector) != self.settings.embedding_dimensions or not all(
                    math.isfinite(value) for value in vector
                ):
                    raise ModelServiceError("嵌入服务返回了无效向量")
                vectors.append(vector)
        return vectors

    async def _post(self, path: str, payload: dict) -> dict:
        try:
            response = await self.client.post(path, json=payload)
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ModelServiceError("嵌入服务暂时不可用，请稍后重试") from exc

    async def close(self) -> None:
        await self.client.aclose()
