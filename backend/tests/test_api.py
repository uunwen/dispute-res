import httpx

from app.main import app


def _client():
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def test_cors_allows_localhost_5173():
    async with _client() as client:
        resp = await client.options(
            "/health",
            headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"},
        )
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"


async def test_list_disputes_newest_first(seeded_session):
    async with _client() as client:
        resp = await client.get("/disputes", params={"include_synthetic": "true"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 2
    for d in data:
        assert {"id", "trip_id", "category", "status", "created_at"} <= d.keys()
    created = [d["created_at"] for d in data]
    assert created == sorted(created, reverse=True)


async def test_list_disputes_default_hides_legacy_seeded(seeded_session):
    # Legacy seeded disputes have a null external_id, so the default
    # (include_synthetic=false) view must not return them.
    async with _client() as client:
        resp = await client.get("/disputes")
    assert resp.status_code == 200
    data = resp.json()
    assert all(d["external_id"] is not None for d in data)


async def test_create_dispute_derives_filed_by_from_trip(seeded_session, ground_truth):
    from sqlalchemy import delete

    from app.db import models
    from app.db.session import async_session_factory
    from app.queue.queue import remove_dispute

    entry = next(e for e in ground_truth if e["label"] == "route_deviation")
    dispute_id = None
    try:
        async with _client() as client:
            resp = await client.post(
                "/disputes",
                json={
                    "trip_id": entry["trip_id"],
                    "category": "route_deviation",
                    "claim_text": "test derived filed_by",
                },
            )
            assert resp.status_code == 201, resp.text
            body = resp.json()
            dispute_id = body["id"]
            assert body["filed_by"] == entry["rider_id"]
    finally:
        if dispute_id is not None:
            await remove_dispute(dispute_id)
            async with async_session_factory() as session:
                await session.execute(delete(models.Dispute).where(models.Dispute.id == dispute_id))
                await session.commit()


async def test_create_dispute_rejects_foreign_filed_by(seeded_session, ground_truth):
    entry = next(e for e in ground_truth if e["label"] == "route_deviation")
    # 999 is not a party on the trip.
    async with _client() as client:
        resp = await client.post(
            "/disputes",
            json={
                "trip_id": entry["trip_id"],
                "category": "route_deviation",
                "claim_text": "test foreign filed_by",
                "filed_by": 999,
            },
        )
    assert resp.status_code == 400


async def test_list_trips(seeded_session):
    async with _client() as client:
        resp = await client.get("/trips")
    assert resp.status_code == 200
    data = resp.json()
    assert data
    for t in data:
        assert {"id", "rider", "driver", "fare", "scenario"} <= t.keys()
        assert isinstance(t["rider"], str) and t["rider"]
        assert isinstance(t["driver"], str) and t["driver"]
        assert isinstance(t["fare"], (int, float))


async def test_get_trip_chat(seeded_session, ground_truth):
    trip_id = next(e["trip_id"] for e in ground_truth if e["label"] == "route_deviation")
    async with _client() as client:
        resp = await client.get(f"/trips/{trip_id}/chat")
    assert resp.status_code == 200
    data = resp.json()
    assert data
    for m in data:
        assert {"id", "sender", "text", "ts"} <= m.keys()


async def test_get_trip_gps(seeded_session, ground_truth):
    trip_id = next(e["trip_id"] for e in ground_truth if e["label"] == "route_deviation")
    async with _client() as client:
        resp = await client.get(f"/trips/{trip_id}/gps")
    assert resp.status_code == 200
    data = resp.json()
    assert "optimal_route" in data
    assert "points" in data
    assert data["optimal_route"]
    assert data["points"]
    assert {"lat", "lng", "ts"} <= data["points"][0].keys()
