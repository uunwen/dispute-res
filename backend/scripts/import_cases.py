import asyncio
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.db import models
from app.db.enums import AccountRole, DisputeCategory
from app.db.session import async_session_factory

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
OFFICIAL_DIR = DATA_DIR / "official"

CATEGORY_MAP = {
    "route_deviation": DisputeCategory.route_deviation,
    "no_show_charge": DisputeCategory.no_show,
    "fare_dispute": DisputeCategory.fare_dispute,
}

# Policy v2.1 fare basis (booking fee is surge-exempt; see Section 3.5).
BASE_FARE = 3.0
PER_KM_RATE = 0.65
PER_MIN_RATE = 0.22


def stable_id(s: str) -> int:
    """Deterministic, collision-resistant integer for an official string id."""
    digest = hashlib.sha256(s.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") & 0x7FFFFFFFFFFFFFFF


def parse_ts(value) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)


def _get(d, key, default=None):
    return d.get(key, default) if isinstance(d, dict) else default


async def _upsert_account(session, account_id: int, role: AccountRole, name: str, rating: float) -> models.Account:
    existing = await session.get(models.Account, account_id)
    if existing is not None:
        existing.name = name
        existing.rating = rating
        return existing
    account = models.Account(id=account_id, role=role, name=name, rating=rating)
    session.add(account)
    return account


def _trip_fields(case: dict) -> dict:
    trip = case.get("trip_data") or {}
    ticket = case.get("dispute_ticket") or {}
    fare = case.get("fare_breakdown") or {}

    pickup = trip.get("pickup_location") or {}
    dropoff = trip.get("dropoff_location") or {}

    optimal = case.get("optimal_route") or {}
    waypoints = optimal.get("waypoints") or []
    if waypoints:
        polyline = [[w["lat"], w["lng"]] for w in waypoints if "lat" in w and "lng" in w]
    elif pickup.get("lat") is not None:
        polyline = [[pickup["lat"], pickup["lng"]]]
        if dropoff.get("lat") is not None:
            polyline.append([dropoff["lat"], dropoff["lng"]])
    else:
        polyline = None

    def _fare_val(*keys):
        cur = fare
        for k in keys:
            if isinstance(cur, dict):
                cur = cur.get(k)
            else:
                return None
        return cur

    surge = _fare_val("actual_fare", "surge_multiplier")
    if surge is None:
        surge_log = case.get("surge_pricing_log") or {}
        surge = surge_log.get("trip_start_surge") or surge_log.get("quote_time_surge") or 1.0

    status = "completed"
    cancellation_fee = 0.0
    if _get(trip, "cancellation_time") is not None:
        status = "cancelled"
        cancellation_fee = float(_get(trip, "cancellation_fee") or 0.0)

    actual_fare = _get(trip, "actual_fare")
    if actual_fare is None:
        actual_fare = _fare_val("actual_fare", "total")
    if actual_fare is None:
        actual_fare = cancellation_fee
    actual_fare = float(actual_fare or 0.0)

    estimated_fare = _get(trip, "estimated_fare")
    if estimated_fare is None:
        estimated_fare = _get(trip, "upfront_quote")
    if estimated_fare is None:
        estimated_fare = _fare_val("upfront_quote", "total")
    estimated_fare = float(estimated_fare or 0.0)

    start_time = _get(trip, "start_time")
    scheduled_time = _get(trip, "scheduled_time")

    pickup_at = parse_ts(start_time)
    dropoff_at = parse_ts(_get(trip, "end_time"))
    requested_at = parse_ts(scheduled_time or start_time) or parse_ts(_get(ticket, "filed_at"))

    return {
        "optimal_route_polyline": polyline,
        "surge_multiplier": float(surge or 1.0),
        "status": status,
        "cancellation_fee": cancellation_fee,
        "actual_fare": actual_fare,
        "estimated_fare": estimated_fare,
        "pickup_at": pickup_at,
        "dropoff_at": dropoff_at,
        "requested_at": requested_at,
        "estimated_distance_km": float(_get(trip, "estimated_distance_km") or 0.0),
        "estimated_duration_min": float(_get(trip, "estimated_duration_min") or 0.0),
    }


def _chat_records(case: dict) -> list[dict]:
    logs = case.get("chat_logs") or []
    records = []
    for entry in logs:
        sender = entry.get("sender")
        if sender not in ("rider", "driver"):
            continue
        records.append(
            {
                "sender": sender,
                "text": entry.get("message") or entry.get("content") or "",
                "ts": entry.get("timestamp"),
            }
        )
    return records


def _gps_records(case: dict) -> list[dict]:
    telemetry = case.get("gps_telemetry") or []
    return [
        {
            "lat": entry.get("lat"),
            "lng": entry.get("lng"),
            "ts": entry.get("timestamp"),
            "speed_kmh": entry.get("speed_kmh"),
        }
        for entry in telemetry
        if entry.get("lat") is not None and entry.get("lng") is not None
    ]


async def _import_case(session, case: dict) -> bool:
    ticket = case.get("dispute_ticket") or {}
    dispute_id = ticket.get("dispute_id")
    if not dispute_id:
        return False

    existing = (
        await session.execute(
            select(models.Dispute.id).where(models.Dispute.external_id == dispute_id)
        )
    ).scalar_one_or_none()
    if existing is not None:
        return False  # already imported

    rider = case.get("rider_profile") or {}
    driver = case.get("driver_profile") or {}
    trip = case.get("trip_data") or {}

    rider_id_str = _get(trip, "rider_id") or rider.get("rider_id")
    driver_id_str = _get(trip, "driver_id") or driver.get("driver_id")
    rider_id = stable_id(rider_id_str) if rider_id_str else stable_id(dispute_id + ":rider")
    driver_id = stable_id(driver_id_str) if driver_id_str else stable_id(dispute_id + ":driver")

    await _upsert_account(
        session, rider_id, AccountRole.rider,
        rider.get("name") or "Rider", float(rider.get("avg_rating") or 5.0),
    )
    await _upsert_account(
        session, driver_id, AccountRole.driver,
        driver.get("name") or "Driver", float(driver.get("avg_rating") or 5.0),
    )
    await session.flush()

    fields = _trip_fields(case)
    trip_row = models.Trip(
        rider_id=rider_id,
        driver_id=driver_id,
        requested_at=fields["requested_at"],
        pickup_at=fields["pickup_at"],
        dropoff_at=fields["dropoff_at"],
        estimated_fare=fields["estimated_fare"],
        actual_fare=fields["actual_fare"],
        surge_multiplier=fields["surge_multiplier"],
        promo_code=None,
        promo_discount=0.0,
        base_fare=BASE_FARE,
        per_km_rate=PER_KM_RATE,
        per_min_rate=PER_MIN_RATE,
        cancellation_fee=fields["cancellation_fee"],
        status=fields["status"],
        estimated_distance_km=fields["estimated_distance_km"],
        estimated_duration_min=fields["estimated_duration_min"],
        optimal_route_polyline=fields["optimal_route_polyline"],
        raw_case=case,
    )
    session.add(trip_row)
    await session.flush()

    for g in _gps_records(case):
        session.add(
            models.GpsPoint(
                trip_id=trip_row.id,
                lat=float(g["lat"]),
                lng=float(g["lng"]),
                ts=parse_ts(g["ts"]),
                speed_kmh=float(g["speed_kmh"]) if g["speed_kmh"] is not None else None,
            )
        )

    for c in _chat_records(case):
        sender_id = rider_id if c["sender"] == "rider" else driver_id
        session.add(
            models.ChatMessage(
                trip_id=trip_row.id,
                sender_id=sender_id,
                text=c["text"],
                ts=parse_ts(c["ts"]),
            )
        )

    category_raw = ticket.get("dispute_type")
    category = CATEGORY_MAP.get(category_raw)
    if category is None:
        raise ValueError(f"{dispute_id}: unsupported dispute_type {category_raw!r}")

    filed_by = driver_id if ticket.get("filed_by") == "driver" else rider_id
    session.add(
        models.Dispute(
            trip_id=trip_row.id,
            filed_by=filed_by,
            category=category,
            claim_text=ticket.get("description") or "",
            status=ticket.get("status") or "open",
            priority=ticket.get("priority") or "medium",
            external_id=dispute_id,
            created_at=parse_ts(ticket.get("filed_at")),
        )
    )
    return True


async def import_official(session) -> tuple[int, int]:
    """Import every case under data/official/ into ``session`` (idempotent)."""
    files = sorted(OFFICIAL_DIR.glob("*.json"))
    imported = 0
    skipped = 0
    for path in files:
        case = json.loads(path.read_text(encoding="utf-8"))
        if await _import_case(session, case):
            imported += 1
        else:
            skipped += 1
    await session.commit()
    return imported, skipped


async def main() -> None:
    async with async_session_factory() as session:
        imported, skipped = await import_official(session)

    if imported + skipped == 0:
        print(f"No official cases found in {OFFICIAL_DIR}")
        return
    print(f"Imported {imported} case(s), skipped {skipped} already-present.")


if __name__ == "__main__":
    asyncio.run(main())
