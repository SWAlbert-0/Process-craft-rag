import httpx
import pytest

from app.config import Settings
from app.services.llm import LLMClient, ModelOutputError


async def test_truncated_reasoning_is_output_error_without_retry() -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            200,
            json={"choices": [{"finish_reason": "length", "message": {"content": ""}}]},
        )

    client = LLMClient(Settings(llm_api_key="test-only", model_max_retries=2))
    await client.close()
    client.client = httpx.AsyncClient(
        base_url="http://test", transport=httpx.MockTransport(handler)
    )
    try:
        with pytest.raises(ModelOutputError, match="token 上限"):
            await client.complete_json("system", "user")
    finally:
        await client.close()
    assert calls == 1


async def test_valid_json_returns_usage() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"content": '{"answer":"ok"}'},
                    }
                ],
                "usage": {"total_tokens": 3},
            },
        )

    client = LLMClient(Settings(llm_api_key="test-only", model_max_retries=0))
    await client.close()
    client.client = httpx.AsyncClient(
        base_url="http://test", transport=httpx.MockTransport(handler)
    )
    try:
        payload, usage = await client.complete_json("system", "user")
    finally:
        await client.close()
    assert payload == {"answer": "ok"}
    assert usage == {"total_tokens": 3}
