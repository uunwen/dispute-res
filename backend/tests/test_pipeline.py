import httpx

from app.main import app


async def test_health_endpoint():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "embedding_provider" in body
    assert "embedding_model" in body
    assert body["embedding_dimension"] > 0


async def test_create_and_get_dispute(seeded_session, ground_truth):
    from sqlalchemy import delete

    from app.db import models
    from app.db.session import async_session_factory
    from app.queue.queue import remove_dispute

    entry = next(e for e in ground_truth if e["label"] == "route_deviation")
    dispute_id = None
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/disputes",
                json={
                    "trip_id": entry["trip_id"],
                    "category": "route_deviation",
                    "claim_text": "driver deviated from the route",
                    "filed_by": entry["rider_id"],
                },
            )
            assert resp.status_code == 201
            dispute_id = resp.json()["id"]

            resp2 = await client.get(f"/disputes/{dispute_id}")
            assert resp2.status_code == 200
            assert resp2.json()["id"] == dispute_id
            assert resp2.json()["category"] == "route_deviation"
    finally:
        if dispute_id is not None:
            await remove_dispute(dispute_id)
            async with async_session_factory() as session:
                await session.execute(delete(models.Dispute).where(models.Dispute.id == dispute_id))
                await session.commit()


async def test_pipeline_resolves_two_categories(seeded_session, ground_truth, monkeypatch):
    from app.db import models
    from app.db.session import async_session_factory
    from app.llm.client import client
    from app.orchestrator.pipeline import resolve_dispute

    monkeypatch.setattr(client, "mock", True)

    async def fake_retrieve(query, category=None, k=4, session=None):
        return [{"source": category or "route_deviation", "section": "1", "text": "policy", "similarity": 0.9}]

    monkeypatch.setattr("app.agents.base.retrieve_policy", fake_retrieve)
    monkeypatch.setattr("app.orchestrator.pipeline.retrieve_policy", fake_retrieve)

    route_entry = next(e for e in ground_truth if e["label"] == "route_deviation")
    no_show_entry = next(e for e in ground_truth if e["label"] == "driver_no_show")

    route_ruling = await resolve_dispute(route_entry["dispute_id"], rebuttal=True)
    no_show_ruling = await resolve_dispute(no_show_entry["dispute_id"], rebuttal=True)

    assert route_ruling.id is not None
    assert no_show_ruling.id is not None
    assert route_ruling.outcome.value == "full_refund"
    assert route_ruling.refund_amount > 0
    assert no_show_ruling.outcome.value == "full_refund"
    assert no_show_ruling.refund_amount > 0

    async with async_session_factory() as session:
        r1 = await session.get(models.Ruling, route_ruling.id)
        r2 = await session.get(models.Ruling, no_show_ruling.id)
    assert r1 is not None and r1.dispute_id == route_entry["dispute_id"]
    assert r2 is not None and r2.dispute_id == no_show_entry["dispute_id"]
