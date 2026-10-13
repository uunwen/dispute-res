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
        resp = await client.get("/disputes")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 2
    for d in data:
        assert {"id", "trip_id", "category", "status", "created_at"} <= d.keys()
    created = [d["created_at"] for d in data]
    assert created == sorted(created, reverse=True)


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
