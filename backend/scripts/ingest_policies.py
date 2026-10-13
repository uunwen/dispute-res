import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text

from app.config import settings
from app.db import models
from app.db.session import async_session_factory
from app.llm.embeddings import embeddings
from app.rag.chunking import chunk_markdown

POLICIES_DIR = Path(__file__).resolve().parents[1] / "policies"


async def main() -> None:
    files = sorted(POLICIES_DIR.glob("*.md"))
    chunks: list[tuple[str, str, str]] = []
    for path in files:
        source = path.stem
        for chunk in chunk_markdown(path.read_text(encoding="utf-8")):
            chunks.append((source, chunk["section"], chunk["text"]))

    texts = [c[2] for c in chunks]
    vecs = await embeddings.embed_texts(texts)

    provider = embeddings.active_provider
    model = embeddings.active_model
    dim = len(vecs[0]) if vecs else settings.embedding_dim

    async with async_session_factory() as session:
        await session.execute(text("TRUNCATE TABLE policy_chunks RESTART IDENTITY"))
        await session.commit()
        for (source, section, txt), vec in zip(chunks, vecs):
            session.add(
                models.PolicyChunk(
                    source=source,
                    section=section,
                    text=txt,
                    embedding=vec,
                    embedding_provider=provider,
                    embedding_model=model,
                )
            )
        await session.commit()

    print(f"Ingested {len(chunks)} chunks from {len(files)} policies "
          f"(provider={provider}, model={model}, dim={dim})")

    if settings.embedding_api_key and provider != "api":
        print(
            "ERROR: an embedding API key is configured but embedding fell back to "
            f"local fastembed (reason: {embeddings.fallback_reason}). "
            "Refusing to ingest a mismatched embedding space.",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
