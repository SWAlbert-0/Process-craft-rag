import httpx

from app.config import Settings
from app.services.domain import Candidate
from app.services.embeddings import ModelServiceError


class RerankClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        key = settings.dashscope_api_key.get_secret_value()
        if not key:
            raise ModelServiceError("尚未配置重排序服务密钥")
        headers = {"Authorization": f"Bearer {key}"}
        if settings.dashscope_workspace_id:
            headers["X-DashScope-WorkSpace"] = settings.dashscope_workspace_id
        self.client = httpx.AsyncClient(headers=headers, timeout=settings.llm_timeout_seconds)

    async def rerank(self, query: str, candidates: list[Candidate], top_n: int) -> list[Candidate]:
        if not candidates:
            return []
        payload = {
            "model": self.settings.rerank_model,
            "input": {
                "query": query,
                "documents": [candidate.hit.text[:4000] for candidate in candidates],
            },
            "parameters": {"return_documents": False, "top_n": min(top_n, len(candidates))},
        }
        try:
            response = await self.client.post(self.settings.rerank_url, json=payload)
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ModelServiceError("重排序服务暂时不可用，请稍后重试") from exc

        results = data.get("output", {}).get("results")
        if not isinstance(results, list):
            raise ModelServiceError("重排序服务返回格式不正确")
        ranked: list[Candidate] = []
        seen: set[int] = set()
        for result in results:
            index = result.get("index")
            score = result.get("relevance_score")
            if not isinstance(index, int) or not 0 <= index < len(candidates) or index in seen:
                raise ModelServiceError("重排序服务返回了无效候选索引")
            if not isinstance(score, int | float):
                raise ModelServiceError("重排序服务返回了无效分数")
            seen.add(index)
            candidate = candidates[index]
            candidate.rerank_score = float(score)
            ranked.append(candidate)
        ranked.sort(key=lambda candidate: candidate.rerank_score or 0.0, reverse=True)
        for rank, candidate in enumerate(ranked, start=1):
            candidate.rerank_rank = rank
        return ranked

    async def close(self) -> None:
        await self.client.aclose()
