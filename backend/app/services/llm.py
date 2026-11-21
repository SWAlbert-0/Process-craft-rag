import asyncio
import json

import httpx

from app.config import Settings
from app.services.embeddings import ModelServiceError


class ModelOutputError(ModelServiceError):
    pass


class LLMClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        key = settings.llm_api_key.get_secret_value()
        if not key:
            raise ModelServiceError("尚未配置大模型服务密钥")
        self.client = httpx.AsyncClient(
            base_url=settings.llm_base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {key}"},
            timeout=settings.llm_timeout_seconds,
        )

    async def complete_json(self, system: str, user: str) -> tuple[dict, dict]:
        payload = {
            "model": self.settings.llm_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
            "max_tokens": self.settings.llm_max_output_tokens,
            "stream": False,
        }
        last_network_error: httpx.HTTPError | None = None
        last_output_error: Exception | None = None
        for attempt in range(self.settings.model_max_retries + 1):
            try:
                response = await self.client.post("/chat/completions", json=payload)
                if response.status_code == 429 or response.status_code >= 500:
                    response.raise_for_status()
                if response.status_code >= 400:
                    raise ModelServiceError("大模型服务拒绝了本次请求，请检查模型配置")
            except ModelServiceError:
                raise
            except httpx.HTTPError as exc:
                last_network_error = exc
                if attempt < self.settings.model_max_retries:
                    await asyncio.sleep(0.5 * (2**attempt))
                continue

            try:
                data = response.json()
                choice = data["choices"][0]
                if choice.get("finish_reason") == "length":
                    raise ModelOutputError("模型输出达到 token 上限，请缩短请求或提高输出预算")
                content = choice["message"]["content"]
                if not isinstance(content, str):
                    raise ValueError("non-text response")
                content = content.strip()
                if content.startswith("```"):
                    content = content.removeprefix("```json").removeprefix("```")
                    content = content.removesuffix("```").strip()
                return json.loads(content), data.get("usage", {})
            except ModelOutputError:
                raise
            except (ValueError, KeyError, IndexError, TypeError) as exc:
                last_output_error = exc
                if attempt < self.settings.model_max_retries:
                    await asyncio.sleep(0.5 * (2**attempt))

        if last_output_error:
            raise ModelOutputError("大模型返回的 JSON 无法解析，请重试") from last_output_error
        raise ModelServiceError("大模型服务暂时不可用，请稍后重试") from last_network_error

    async def close(self) -> None:
        await self.client.aclose()
