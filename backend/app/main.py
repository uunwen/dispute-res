import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.formulas import formulas_markdown
from app.llm.client import log_llm_config
from app.llm.embeddings import embeddings

logger = logging.getLogger(__name__)

_DESCRIPTION = """
Multi-agent autonomous dispute resolution system for ride-hailing.

Three core agents resolve disputes end-to-end without human intervention:

* **Rider Advocate** — gathers rider-side evidence and argues for rider-favorable outcomes.
* **Driver Advocate** — gathers driver-side evidence and argues for driver-favorable outcomes.
* **Judge** — weighs both briefs, applies policy, issues a ruling (refund / partial refund /
  no action) with a confidence score and natural-language reasoning.

The rules engine is the deterministic source of truth for every monetary amount; the LLM
never performs arithmetic. See `GET /meta/formulas` for the full list of calculations.

Interactive API documentation: `/docs` (Swagger UI) and `/redoc` (ReDoc).
"""

_TAGS_METADATA = [
    {"name": "Disputes", "description": "File, resolve and inspect disputes and their rulings."},
    {"name": "Trips", "description": "Inspect trips, GPS, chat and computed evidence."},
    {"name": "Queue", "description": "Priority queue and SLA routing."},
    {"name": "Meta", "description": "System metadata, supported categories and formulas."},
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    log_llm_config()
    yield


app = FastAPI(
    title="Dispute Resolver",
    version="0.1.0",
    description=_DESCRIPTION + "\n\n" + formulas_markdown(),
    openapi_tags=_TAGS_METADATA,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health", tags=["Meta"], summary="Health check")
async def health():
    return {
        "status": "ok",
        "embedding_provider": embeddings.active_provider,
        "embedding_model": embeddings.active_model,
        "embedding_dimension": embeddings.dimension,
        "embedding_fallback_reason": embeddings.fallback_reason,
    }


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error: %s", exc)
    return JSONResponse(status_code=500, content={"detail": str(exc)})
