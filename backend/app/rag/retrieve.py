import time

from sqlalchemy import func, select

from app.config import settings
from app.db import models
from app.db.session import async_session_factory
from app.llm.embeddings import embeddings
from app.profiling import profiler

# Maps a dispute category to the policy file that backs it (the file names keep
# their own naming, e.g. no_show_fee.md, fare_surge_promo.md).
_CATEGORY_TO_SOURCE = {
    "route_deviation": "route_deviation",
    "no_show": "no_show_fee",
    "fare_dispute": "fare_surge_promo",
    "safety_incident": "safety_incident",
    "property_damage": "property_damage",
}

# Precedents (Policy v2.1 Section 7) are ingested under this source tag.
_PRECEDENT_SOURCE = "precedent"

# Retrieval budget: up to 3 policy chunks and 2 precedents per dispute.
_MAX_POLICY_K = 3
_MAX_PRECEDENT_K = 2

# Policy retrieval is deterministic (static chunks, same query + category) so its
# results can be shared. Both advocates issue the same query for a dispute; this
# cache avoids redundant embedding + vector-search round-trips.
_retrieval_cache: dict[tuple, list[dict]] = {}


class EmbeddingSpaceMismatchError(Exception):
    """The query embedding and stored policy chunks live in different spaces."""


def _query_signature(qvec: list[float]) -> tuple[str, str, int]:
    return (embeddings.active_provider, embeddings.active_model, len(qvec))


def _normalize_query(query: str) -> str:
    return " ".join(query.lower().split())


def clear_retrieval_cache() -> None:
    _retrieval_cache.clear()


async def retrieve_policy(query: str, category: str | None = None, k: int = 3, session=None) -> list[dict]:
    """Return the most similar policy chunks plus precedents for ``query``.

    Up to ``k`` (max 3) policy chunks for the dispute category and up to 2
    precedent rulings are returned together. Each result includes ``source``,
    ``section``, ``text`` and ``similarity`` so agents can cite it. Results below
    the configured minimum similarity cutoff are dropped.

    Refuses to run if the query embedding's provider/model/dimension differs from
    what the stored chunks were ingested with, to never silently compare vectors
    from different models.
    """
    start = time.perf_counter()
    try:
        k = max(1, min(k, _MAX_POLICY_K))
        key = (category, _normalize_query(query), k, embeddings.active_provider, embeddings.active_model)
        cached = _retrieval_cache.get(key)
        if cached is not None:
            return cached

        results = await _retrieve(query, category=category, k=k, session=session)
        results = [r for r in results if r["similarity"] >= settings.embedding_similarity_cutoff]
        _retrieval_cache[key] = results
        return results
    finally:
        profiler.record("policy_retrieval", time.perf_counter() - start)


def _to_result(row) -> dict:
    return {
        "source": row.source,
        "section": row.section,
        "text": row.text,
        "similarity": round(1.0 - row.distance, 4),
    }


async def _retrieve(query: str, category: str | None, k: int, session) -> list[dict]:
    vecs = await embeddings.embed_texts([query])
    if not vecs:
        return []
    qvec = vecs[0]
    query_sig = _query_signature(qvec)

    async def _run(s):
        stored = (
            await s.execute(
                select(
                    models.PolicyChunk.embedding_provider,
                    models.PolicyChunk.embedding_model,
                    func.vector_dims(models.PolicyChunk.embedding).label("dim"),
                ).limit(1)
            )
        ).first()
        if stored is None:
            raise EmbeddingSpaceMismatchError(
                "policy_chunks is empty; run scripts/ingest_policies.py first"
            )
        stored_sig = (stored[0], stored[1], stored[2])
        if stored_sig != query_sig:
            raise EmbeddingSpaceMismatchError(
                "embedding space mismatch: policy chunks were ingested with "
                f"(provider={stored[0]}, model={stored[1]}, dim={stored[2]}) but the "
                f"query uses (provider={query_sig[0]}, model={query_sig[1]}, "
                f"dim={query_sig[2]}); re-run scripts/ingest_policies.py"
            )

        distance = models.PolicyChunk.embedding.cosine_distance(qvec)
        base = select(
            models.PolicyChunk.id,
            models.PolicyChunk.source,
            models.PolicyChunk.section,
            models.PolicyChunk.text,
            distance.label("distance"),
        )

        policy_stmt = base.where(models.PolicyChunk.source != _PRECEDENT_SOURCE)
        if category:
            source = _CATEGORY_TO_SOURCE.get(category, category)
            policy_stmt = policy_stmt.where(models.PolicyChunk.source == source)
        policy_stmt = policy_stmt.order_by(distance).limit(k)
        policy_rows = (await s.execute(policy_stmt)).all()

        precedent_stmt = (
            base.where(models.PolicyChunk.source == _PRECEDENT_SOURCE)
            .order_by(distance)
            .limit(_MAX_PRECEDENT_K)
        )
        precedent_rows = (await s.execute(precedent_stmt)).all()

        return [_to_result(r) for r in policy_rows] + [_to_result(r) for r in precedent_rows]

    if session is not None:
        return await _run(session)
    async with async_session_factory() as s:
        return await _run(s)
