import pytest

from app.llm import embeddings as emb_mod
from app.llm.embeddings import (
    EmbeddingDimensionError,
    EmbeddingResponseError,
    Embeddings,
    _parse_embeddings_response,
)


# --- parser tests ---


def test_parse_openai_style_sorts_by_index():
    data = {
        "data": [
            {"object": "embedding", "index": 1, "embedding": [0.0, 0.1]},
            {"object": "embedding", "index": 0, "embedding": [1.0, 1.1]},
        ]
    }
    assert _parse_embeddings_response(data, 2) == [[1.0, 1.1], [0.0, 0.1]]


def test_parse_gemini_style_no_index_keeps_order():
    data = {
        "data": [
            {"object": "embedding", "embedding": [1.0, 1.1]},
            {"object": "embedding", "embedding": [0.0, 0.1]},
        ]
    }
    assert _parse_embeddings_response(data, 2) == [[1.0, 1.1], [0.0, 0.1]]


def test_parse_malformed_body_raises():
    with pytest.raises(EmbeddingResponseError):
        _parse_embeddings_response({"unexpected": "shape"}, 1)
    with pytest.raises(EmbeddingResponseError):
        _parse_embeddings_response({"data": []}, 1)
    with pytest.raises(EmbeddingResponseError):
        _parse_embeddings_response({"data": [{"object": "embedding"}]}, 1)
    with pytest.raises(EmbeddingResponseError):
        _parse_embeddings_response({"data": [{"embedding": [1.0]}]}, 2)


# --- provider selection ---


def test_provider_defaults_to_fastembed_without_key(monkeypatch):
    monkeypatch.setattr(emb_mod.settings, "embedding_api_key", "")
    assert emb_mod.embeddings.provider == "fastembed"


def test_provider_uses_api_with_key(monkeypatch):
    monkeypatch.setattr(emb_mod.settings, "embedding_api_key", "test-key")
    assert emb_mod.embeddings.provider == "api"


# --- embed_texts behavior ---


async def test_embed_texts_uses_api_when_available(monkeypatch):
    emb = Embeddings()
    monkeypatch.setattr(emb_mod.settings, "embedding_api_key", "test-key")
    monkeypatch.setattr(emb_mod.settings, "embedding_dim", 3)
    monkeypatch.setattr(emb_mod.settings, "embedding_model", "m")

    async def fake_api(texts):
        return [[0.1, 0.2, 0.3] for _ in texts]

    monkeypatch.setattr(emb, "_embed_api", fake_api)

    vecs = await emb.embed_texts(["a", "b"])
    assert vecs == [[0.1, 0.2, 0.3], [0.1, 0.2, 0.3]]
    assert emb.active_provider == "api"
    assert emb.active_model == "m"
    assert emb.fallback_reason is None


async def test_embed_texts_falls_back_to_fastembed_on_api_error(monkeypatch):
    emb = Embeddings()
    monkeypatch.setattr(emb_mod.settings, "embedding_api_key", "test-key")
    monkeypatch.setattr(emb_mod.settings, "embedding_dim", 3)

    async def boom(texts):
        raise RuntimeError("embeddings api down")

    def fake_fastembed(texts):
        return [[0.1, 0.2, 0.3] for _ in texts]

    monkeypatch.setattr(emb, "_embed_api", boom)
    monkeypatch.setattr(emb, "_embed_fastembed", fake_fastembed)

    vecs = await emb.embed_texts(["hello", "world"])
    assert vecs == [[0.1, 0.2, 0.3], [0.1, 0.2, 0.3]]
    assert emb.active_provider == "fastembed"
    assert emb.fallback_reason is not None


async def test_embed_texts_raises_when_fastembed_dimension_differs(monkeypatch):
    emb = Embeddings()
    monkeypatch.setattr(emb_mod.settings, "embedding_api_key", "")
    monkeypatch.setattr(emb_mod.settings, "embedding_dim", 4)

    def fake_fastembed(texts):
        return [[0.1, 0.2, 0.3] for _ in texts]  # dim 3 != EMBEDDING_DIM 4

    monkeypatch.setattr(emb, "_embed_fastembed", fake_fastembed)

    with pytest.raises(EmbeddingDimensionError):
        await emb.embed_texts(["hello"])


async def test_embed_texts_raises_when_api_dimension_differs(monkeypatch):
    emb = Embeddings()
    monkeypatch.setattr(emb_mod.settings, "embedding_api_key", "test-key")
    monkeypatch.setattr(emb_mod.settings, "embedding_dim", 3)

    async def wrong_dim_api(texts):
        return [[0.1, 0.2, 0.3, 0.4] for _ in texts]  # dim 4 != EMBEDDING_DIM 3

    monkeypatch.setattr(emb, "_embed_api", wrong_dim_api)

    with pytest.raises(EmbeddingDimensionError):
        await emb.embed_texts(["hello"])


async def test_embed_texts_api_error_then_fastembed_wrong_dim_raises(monkeypatch):
    emb = Embeddings()
    monkeypatch.setattr(emb_mod.settings, "embedding_api_key", "test-key")
    monkeypatch.setattr(emb_mod.settings, "embedding_dim", 4)

    async def boom(texts):
        raise RuntimeError("down")

    def fake_fastembed(texts):
        return [[0.1, 0.2, 0.3] for _ in texts]  # dim 3 != EMBEDDING_DIM 4

    monkeypatch.setattr(emb, "_embed_api", boom)
    monkeypatch.setattr(emb, "_embed_fastembed", fake_fastembed)

    with pytest.raises(EmbeddingDimensionError):
        await emb.embed_texts(["hello"])
    assert emb.fallback_reason is not None
