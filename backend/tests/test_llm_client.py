import httpx
import pytest
from pydantic import BaseModel

from app.llm.client import LLMClient, LLMError, Usage, _mock_instance, _mock_value


class _MockSchema(BaseModel):
    answer: str
    confidence: float
    tags: list[str] = []


def test_mock_value_types():
    assert _mock_value(str) == "mock"
    assert _mock_value(int) == 0
    assert _mock_value(float) == 0.0
    assert _mock_value(bool) is False
    assert _mock_value(list[int]) == []
    assert _mock_value(str | None) == "mock"


def test_mock_instance_fills_required_fields():
    inst = _mock_instance(_MockSchema)
    assert isinstance(inst, _MockSchema)
    assert inst.answer == "mock"
    assert inst.confidence == 0.0
    assert inst.tags == []


async def test_mock_structured_returns_valid_instance():
    client = LLMClient(mock=True)
    result = await client.structured("sys", "user", _MockSchema)
    assert isinstance(result, _MockSchema)
    assert result.answer == "mock"
    assert result.confidence == 0.0


async def test_mock_structured_is_deterministic():
    client = LLMClient(mock=True)
    a = await client.structured("sys", "user", _MockSchema)
    b = await client.structured("sys", "user", _MockSchema)
    assert a.model_dump() == b.model_dump()


async def test_mock_chat_returns_canned_content():
    client = LLMClient(mock=True)
    result = await client.chat([{"role": "user", "content": "hello"}])
    assert result.content == "This is a mock response."
    assert result.tool_calls == []
    assert result.usage == Usage()


def test_configured_flags():
    client = LLMClient(mock=True)
    assert client.configured is True
    client = LLMClient(mock=False)
    client.api_key = "k"
    assert client.configured is True
    client.api_key = ""
    assert client.configured is False


async def test_structured_retries_on_validation_failure(monkeypatch):
    client = LLMClient(base_url="http://localhost", api_key="k", model="m", mock=False)
    calls = {"n": 0}

    async def fake_complete(messages, *, json_mode=False, role="advocate"):
        calls["n"] += 1
        if calls["n"] == 1:
            return '{"wrong": true}'
        return '{"answer": "ok", "confidence": 0.9}'

    monkeypatch.setattr(client, "_complete_content", fake_complete)
    result = await client.structured("sys", "user", _MockSchema)
    assert result.answer == "ok"
    assert result.confidence == 0.9
    assert calls["n"] == 2


async def test_structured_raises_after_retries(monkeypatch):
    client = LLMClient(base_url="http://localhost", api_key="k", model="m", mock=False)

    async def fake_complete(messages, *, json_mode=False, role="advocate"):
        return "not-json"

    monkeypatch.setattr(client, "_complete_content", fake_complete)
    with pytest.raises(LLMError):
        await client.structured("sys", "user", _MockSchema)


def test_model_for_role_defaults(monkeypatch):
    from app.config import settings
    from app.llm.client import model_for_role

    monkeypatch.setattr(settings, "llm_model", "default-model")
    monkeypatch.setattr(settings, "llm_model_advocate", "")
    monkeypatch.setattr(settings, "llm_model_judge", "")
    monkeypatch.setattr(settings, "llm_model_tools", "")

    assert model_for_role("advocate") == "default-model"
    assert model_for_role("judge") == "default-model"
    assert model_for_role("tools") == "default-model"
    assert model_for_role("unknown") == "default-model"


def test_model_for_role_override(monkeypatch):
    from app.config import settings
    from app.llm.client import model_for_role

    monkeypatch.setattr(settings, "llm_model", "default-model")
    monkeypatch.setattr(settings, "llm_model_advocate", "adv-model")
    monkeypatch.setattr(settings, "llm_model_judge", "judge-model")
    monkeypatch.setattr(settings, "llm_model_tools", "tools-model")

    assert model_for_role("advocate") == "adv-model"
    assert model_for_role("judge") == "judge-model"
    assert model_for_role("tools") == "tools-model"


class _FakeHTTP:
    def __init__(self, status_code: int):
        self.status_code = status_code
        self.calls = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args, **kwargs):
        return False

    async def post(self, url, *, headers=None, json=None):
        self.calls += 1
        request = httpx.Request("POST", url)
        return httpx.Response(self.status_code, request=request)


async def _noop_backoff(attempt):
    pass


async def test_400_sets_degraded_and_error_info(monkeypatch):
    fake = _FakeHTTP(400)
    monkeypatch.setattr(httpx, "AsyncClient", lambda timeout=None: fake)

    client = LLMClient(base_url="http://test", api_key="k", model="m", mock=False)
    with pytest.raises(LLMError):
        await client.chat([{"role": "user", "content": "hi"}])

    assert client.degraded is True
    assert client.error_info == {"class": "HTTPStatusError", "status": 400}
    assert fake.calls == 1


async def test_429_retries_with_backoff_and_sets_degraded(monkeypatch):
    fake = _FakeHTTP(429)
    monkeypatch.setattr(httpx, "AsyncClient", lambda timeout=None: fake)

    client = LLMClient(base_url="http://test", api_key="k", model="m", mock=False)
    monkeypatch.setattr(client, "_backoff", _noop_backoff)

    with pytest.raises(LLMError):
        await client.chat([{"role": "user", "content": "hi"}])

    assert client.degraded is True
    assert client.error_info == {"class": "HTTPStatusError", "status": 429}
    assert fake.calls == client.max_retries + 1
