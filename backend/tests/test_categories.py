from app.db.enums import DisputeCategory
from app.schemas.api import DisputeCreate


def test_legacy_aliases_normalised():
    assert DisputeCreate(trip_id=1, category="cancellation_fee", claim_text="x", filed_by=1).category is DisputeCategory.no_show
    assert DisputeCreate(trip_id=1, category="surge_pricing", claim_text="x", filed_by=1).category is DisputeCategory.fare_dispute
    assert DisputeCreate(trip_id=1, category="fare", claim_text="x", filed_by=1).category is DisputeCategory.fare_dispute
    assert DisputeCreate(trip_id=1, category="no_show", claim_text="x", filed_by=1).category is DisputeCategory.no_show
    assert DisputeCreate(trip_id=1, category="fare_dispute", claim_text="x", filed_by=1).category is DisputeCategory.fare_dispute


def test_rules_categories_are_valid():
    from app.rules.engine import load_rules

    valid = {c.value for c in DisputeCategory}
    for rule in load_rules():
        assert rule.category in valid, f"rule {rule.id} has invalid category {rule.category!r}"


def test_ground_truth_categories_are_valid(ground_truth):
    valid = {c.value for c in DisputeCategory}
    for entry in ground_truth:
        assert entry["category"] in valid, f"trip {entry['trip_id']} has invalid category {entry['category']!r}"


async def test_all_supported_categories_resolve(seeded_session, ground_truth, monkeypatch):
    import httpx
    from sqlalchemy import delete

    from app.db import models
    from app.db.session import async_session_factory
    from app.llm.client import client
    from app.main import app
    from app.orchestrator.pipeline import resolve_dispute
    from app.queue.queue import remove_dispute

    monkeypatch.setattr(client, "mock", True)

    async def fake_retrieve(query, category=None, k=4, session=None):
        return []

    monkeypatch.setattr("app.agents.base.retrieve_policy", fake_retrieve)
    monkeypatch.setattr("app.orchestrator.pipeline.retrieve_policy", fake_retrieve)

    created: list[int] = []
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
            for category in ("route_deviation", "no_show", "fare_dispute"):
                entry = next(e for e in ground_truth if e["category"] == category)
                resp = await http.post(
                    "/disputes",
                    json={
                        "trip_id": entry["trip_id"],
                        "category": category,
                        "claim_text": f"test {category}",
                        "filed_by": entry["rider_id"],
                    },
                )
                assert resp.status_code == 201, f"{category} got {resp.status_code}: {resp.text}"
                dispute_id = resp.json()["id"]
                created.append(dispute_id)

                ruling = await resolve_dispute(dispute_id, rebuttal=False)
                assert ruling.id is not None
    finally:
        async with async_session_factory() as session:
            for dispute_id in created:
                await remove_dispute(dispute_id)
                await session.execute(delete(models.AgentMessage).where(models.AgentMessage.dispute_id == dispute_id))
                await session.execute(delete(models.Ruling).where(models.Ruling.dispute_id == dispute_id))
                await session.execute(delete(models.Dispute).where(models.Dispute.id == dispute_id))
            await session.commit()
