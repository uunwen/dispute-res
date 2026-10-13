import asyncio
import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class EmbeddingError(Exception):
    """Base class for embedding failures."""


class EmbeddingDimensionError(EmbeddingError):
    """A produced vector does not match EMBEDDING_DIM."""


class EmbeddingResponseError(EmbeddingError):
    """The embeddings API returned a malformed or unexpected response."""


def _parse_embeddings_response(data, n_inputs: int) -> list[list[float]]:
    """Parse an OpenAI-compatible embeddings response into an ordered vector list.

    Does not assume the response shape: if every item carries an ``index`` key the
    items are sorted by it (OpenAI style), otherwise the provider's order is kept
    (Google/Gemini style, which omits ``index``).
    """
    items = data.get("data") if isinstance(data, dict) else None
    if not isinstance(items, list) or not items:
        raise EmbeddingResponseError(
            "embeddings response is missing a non-empty 'data' list "
            f"(keys={list(data.keys()) if isinstance(data, dict) else type(data).__name__})"
        )

    if all(isinstance(item, dict) and "index" in item for item in items):
        items = sorted(items, key=lambda x: x["index"])

    vectors: list[list[float]] = []
    for item in items:
        if not isinstance(item, dict) or "embedding" not in item:
            raise EmbeddingResponseError("embeddings response item is missing the 'embedding' field")
        vectors.append(item["embedding"])

    if len(vectors) != n_inputs:
        raise EmbeddingResponseError(
            f"embeddings returned {len(vectors)} vectors for {n_inputs} inputs"
        )
    return vectors


class Embeddings:
    def __init__(self):
        self._fastembed = None
        self._api_unavailable = False
        self._fallback_reason: str | None = None
        self._active_provider: str | None = None
        self._active_model: str | None = None

    @property
    def provider(self) -> str:
        """The provider selected by configuration (before any fallback)."""
        return "api" if settings.embedding_api_key else "fastembed"

    @property
    def dimension(self) -> int:
        return settings.embedding_dim

    @property
    def active_provider(self) -> str:
        """The provider that actually produced the last vectors (or would)."""
        return self._active_provider or self.provider

    @property
    def active_model(self) -> str:
        if self._active_model:
            return self._active_model
        return settings.embedding_model if self.provider == "api" else settings.fastembed_model

    @property
    def fallback_reason(self) -> str | None:
        """Why the API was abandoned for local fastembed, if it was."""
        return self._fallback_reason

    def warmup(self) -> None:
        """Preload the embedding model so the first retrieval is not slowed down.

        For the local fastembed provider this loads the model into memory; for the
        API provider there is nothing to preload (requests are stateless).
        """
        if self.provider == "fastembed":
            self._load_fastembed()

    def _mark_fallback(self, reason: str) -> None:
        if self._fallback_reason is None:
            logger.warning(
                "Embeddings API unavailable; falling back to local fastembed for the "
                "rest of the process: %s",
                reason,
            )
        self._fallback_reason = reason
        self._api_unavailable = True

    def _validate_dimension(self, vectors: list[list[float]]) -> None:
        if not vectors:
            raise EmbeddingDimensionError("no embeddings were produced")
        for i, vec in enumerate(vectors):
            if len(vec) != settings.embedding_dim:
                raise EmbeddingDimensionError(
                    f"embedding {i} has dimension {len(vec)}, expected "
                    f"EMBEDDING_DIM={settings.embedding_dim}"
                )

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        if self.provider == "api" and not self._api_unavailable:
            try:
                vecs = await self._embed_api(texts)
                self._validate_dimension(vecs)
            except EmbeddingDimensionError:
                # The provider is reachable but returned the wrong dimension: a
                # configuration mismatch, not a transient failure. Never fall
                # back silently into a different embedding space.
                raise
            except Exception as exc:  # noqa: BLE001
                self._mark_fallback(str(exc))
            else:
                self._active_provider = "api"
                self._active_model = settings.embedding_model
                return vecs

        vecs = await asyncio.to_thread(self._embed_fastembed, texts)
        # The fallback must live in the same embedding space; otherwise it is
        # effectively disabled by raising rather than silently mixing spaces.
        self._validate_dimension(vecs)
        self._active_provider = "fastembed"
        self._active_model = settings.fastembed_model
        return vecs

    async def _embed_api(self, texts: list[str]) -> list[list[float]]:
        base = settings.embedding_base_url or settings.llm_base_url
        url = f"{base.rstrip('/')}/embeddings"
        headers = {
            "Authorization": f"Bearer {settings.embedding_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": settings.embedding_model,
            "input": texts,
            # Ask the provider for EMBEDDING_DIM output dimensions. Supported by
            # Google's OpenAI-compatible embeddings API (and OpenAI text-embedding-3).
            "dimensions": settings.embedding_dim,
        }
        async with httpx.AsyncClient(timeout=120) as http:
            resp = await http.post(url, headers=headers, json=payload)
        status = resp.status_code
        body = resp.text
        if status != 200:
            raise EmbeddingResponseError(f"embeddings API HTTP {status}: {body[:300]}")
        try:
            data = resp.json()
        except Exception as exc:  # noqa: BLE001
            raise EmbeddingResponseError(
                f"embeddings API returned non-JSON (HTTP {status}): {body[:300]}"
            ) from exc
        try:
            return _parse_embeddings_response(data, len(texts))
        except EmbeddingResponseError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise EmbeddingResponseError(
                f"embeddings API malformed body (HTTP {status}): {body[:300]}; {exc}"
            ) from exc

    def _load_fastembed(self):
        if self._fastembed is None:
            from fastembed import TextEmbedding

            self._fastembed = TextEmbedding(model_name=settings.fastembed_model)
        return self._fastembed

    def _embed_fastembed(self, texts: list[str]) -> list[list[float]]:
        model = self._load_fastembed()
        return [v.tolist() for v in model.embed(list(texts))]


embeddings = Embeddings()
