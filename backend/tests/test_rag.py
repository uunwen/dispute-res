import pytest
from sqlalchemy import select, text

from app.db import models
from app.llm import embeddings as emb_mod
from app.rag.chunking import chunk_markdown
from app.rag.retrieve import EmbeddingSpaceMismatchError, retrieve_policy


def test_chunk_markdown_splits_sections():
    doc = "# Title\n\n## 1. Definition\nbody one\n\n## 2. Refunds\nbody two\n"
    chunks = chunk_markdown(doc)
    assert [c["section"] for c in chunks] == ["1", "2"]
    assert chunks[0]["text"].startswith("## 1. Definition")
    assert "body one" in chunks[0]["text"]


async def test_retrieve_policy_raises_on_model_mismatch(seeded_session, monkeypatch):
    dim = emb_mod.settings.embedding_dim

    # Replace the table contents inside this session's transaction (no commit),
    # so the change rolls back and the real ingested chunks are left intact.
    await seeded_session.execute(text("TRUNCATE TABLE policy_chunks RESTART IDENTITY"))
    seeded_session.add(
        models.PolicyChunk(
            source="route_deviation",
            section="1",
            text="policy text",
            embedding=[0.0] * dim,
            embedding_provider="fastembed",
            embedding_model="BAAI/bge-small-en-v1.5",
        )
    )
    await seeded_session.flush()

    # Query side claims a different provider/model than what the chunk was
    # ingested with.
    async def fake_embed(texts):
        return [[0.0] * dim for _ in texts]

    monkeypatch.setattr(emb_mod.embeddings, "embed_texts", fake_embed)
    monkeypatch.setattr(emb_mod.embeddings, "_active_provider", "api")
    monkeypatch.setattr(emb_mod.embeddings, "_active_model", "gemini-embedding-001")

    with pytest.raises(EmbeddingSpaceMismatchError):
        await retrieve_policy("driver took a long detour", category=None, session=seeded_session)


async def test_retrieve_policy_returns_cited_chunks(seeded_session):
    has_chunks = (
        await seeded_session.execute(select(models.PolicyChunk.id).limit(1))
    ).first()
    if has_chunks is None:
        pytest.skip("policy_chunks empty; run scripts/ingest_policies.py first")

    results = await retrieve_policy(
        "driver took a long detour", category="route_deviation", k=2, session=seeded_session
    )
    assert results
    for r in results:
        assert r["source"] == "route_deviation"
        assert r["section"]
        assert "similarity" in r
        assert "text" in r


async def test_retrieval_smoke_route_deviation_first(seeded_session):
    has_chunks = (
        await seeded_session.execute(select(models.PolicyChunk.id).limit(1))
    ).first()
    if has_chunks is None:
        pytest.skip("policy_chunks empty; run scripts/ingest_policies.py first")

    results = await retrieve_policy(
        "driver took a longer route", k=5, session=seeded_session
    )
    assert results
    assert results[0]["source"] == "route_deviation"


async def test_retrieval_smoke_no_show_first(seeded_session):
    has_chunks = (
        await seeded_session.execute(select(models.PolicyChunk.id).limit(1))
    ).first()
    if has_chunks is None:
        pytest.skip("policy_chunks empty; run scripts/ingest_policies.py first")

    results = await retrieve_policy(
        "driver didn't show up but I was charged", k=5, session=seeded_session
    )
    assert results
    assert results[0]["source"] == "no_show_fee"
