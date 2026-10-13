import datetime as dt

from app.queue.queue import priority_score


def _now():
    return dt.datetime(2026, 10, 10, 12, 0, 0, tzinfo=dt.timezone.utc)


def test_priority_score_safety_first():
    now = _now()
    safety = priority_score(category="safety_incident", amount=1.0, created_at=now, now=now)
    normal = priority_score(
        category="route_deviation", amount=100000.0, created_at=now - dt.timedelta(days=3650), now=now
    )
    assert safety > normal


def test_priority_score_higher_amount_first():
    now = _now()
    high = priority_score(category="route_deviation", amount=50.0, created_at=now, now=now)
    low = priority_score(
        category="route_deviation", amount=5.0, created_at=now - dt.timedelta(days=3650), now=now
    )
    assert high > low


def test_priority_score_older_first():
    now = _now()
    older = priority_score(category="route_deviation", amount=10.0, created_at=now - dt.timedelta(days=10), now=now)
    newer = priority_score(category="route_deviation", amount=10.0, created_at=now, now=now)
    assert older > newer


async def test_enqueue_pop_order(seeded_session, ground_truth):
    from app.db import models
    from app.db.session import async_session_factory
    from app.queue.queue import clear_queue, enqueue_dispute, pop_dispute

    await clear_queue()
    entries = [e for e in ground_truth if e["label"] == "route_deviation"][:4]
    for e in entries:
        await enqueue_dispute(e["dispute_id"])

    popped = []
    while True:
        dispute_id, _ = await pop_dispute()
        if dispute_id is None:
            break
        popped.append(dispute_id)

    assert set(popped) == {e["dispute_id"] for e in entries}

    async with async_session_factory() as session:
        fares = {}
        for e in entries:
            d = await session.get(models.Dispute, e["dispute_id"])
            t = await session.get(models.Trip, d.trip_id)
            fares[e["dispute_id"]] = t.actual_fare
    expected = [e["dispute_id"] for e in sorted(entries, key=lambda e: fares[e["dispute_id"]], reverse=True)]
    assert popped == expected


async def test_list_queue_reports_sla(seeded_session, ground_truth):
    from app.queue.queue import clear_queue, enqueue_dispute, list_queue

    await clear_queue()
    entry = next(e for e in ground_truth if e["label"] == "route_deviation")
    await enqueue_dispute(entry["dispute_id"])

    items = await list_queue()
    assert len(items) >= 1
    item = next(i for i in items if i["dispute_id"] == entry["dispute_id"])
    assert item["category"] == "route_deviation"
    assert item["sla_seconds"] == 86400
    assert "priority" in item
    assert "wait_time_seconds" in item
    assert "breached" in item
