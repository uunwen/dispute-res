import json
from pathlib import Path

import pytest
from sqlalchemy import select, text

from app.db import models
from app.db.session import async_session_factory

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
OFFICIAL_DIR = DATA_DIR / "official"


def _expected_from_file(dispute_id: str) -> dict:
    case = json.loads((OFFICIAL_DIR / f"{dispute_id}.json").read_text(encoding="utf-8"))
    meta = case.get("case_metadata") or {}
    recommended = case.get("recommended_ruling") or {}
    return {
        "outcome": meta.get("expected_ruling") or recommended.get("ruling"),
        "refund": float(meta.get("expected_refund_amount") or recommended.get("refund_amount") or 0.0),
    }


@pytest.fixture(scope="session", autouse=True)
async def _import_official_cases():
    from scripts.import_cases import import_official

    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
            await import_official(session)
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Database unavailable: {exc}")


@pytest.fixture
async def _resolve_env(monkeypatch):
    from app.llm.client import client

    monkeypatch.setattr(client, "mock", True)

    async def fake_retrieve(query, category=None, k=3, session=None):
        return []

    monkeypatch.setattr("app.agents.base.retrieve_policy", fake_retrieve)
    monkeypatch.setattr("app.orchestrator.pipeline.retrieve_policy", fake_retrieve)


async def _dispute_id(external_id: str) -> int:
    async with async_session_factory() as session:
        return (
            await session.execute(
                select(models.Dispute.id).where(models.Dispute.external_id == external_id)
            )
        ).scalar_one()


async def _resolve(external_id: str) -> models.Ruling:
    from app.orchestrator.pipeline import resolve_dispute

    dispute_id = await _dispute_id(external_id)
    return await resolve_dispute(dispute_id, rebuttal=False)


async def test_disp001_route_deviation_partial_refund(_import_official_cases, _resolve_env):
    expected = _expected_from_file("DISP-001")
    ruling = await _resolve("DISP-001")
    assert expected["outcome"] == "partial_refund"
    assert ruling.outcome.value == "partial_refund"
    assert abs(ruling.refund_amount - expected["refund"]) < 0.01


async def test_disp002_no_show_charge_upheld(_import_official_cases, _resolve_env):
    ruling = await _resolve("DISP-002")
    assert ruling.outcome.value == "no_refund"
    assert ruling.refund_amount == 0.0


async def test_disp003_surge_refund(_import_official_cases, _resolve_env):
    ruling = await _resolve("DISP-003")
    assert ruling.outcome.value == "full_refund"
    assert abs(ruling.refund_amount - 4.50) < 0.01
