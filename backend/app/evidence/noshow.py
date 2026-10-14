from sqlalchemy import select

from app.config import settings
from app.db import models
from app.db.session import async_session_factory
from app.evidence.base import result_to_evidence
from app.evidence.route import haversine_km
from app.schemas.evidence import EvidenceItem


def compute_noshow(
    pickup,
    gps_points,
    *,
    proximity_m=100.0,
    min_wait_min=5.0,
    rider_reachable=None,
):
    """Classify driver/rider no-show from GPS fixes relative to the pickup point.

    ``pickup`` is a ``(lat, lng)`` tuple and ``gps_points`` is a list of
    ``(lat, lng, ts, speed_kmh)`` tuples sorted by time. Pure and deterministic.
    """
    n = len(gps_points)
    if n == 0:
        return {
            "supports": "neutral",
            "strength": 0.0,
            "summary": "No GPS data available for no-show analysis.",
            "data": {"error": "no_data"},
        }

    dists_m = [haversine_km((lat, lng), pickup) * 1000.0 for lat, lng, _ts, _spd in gps_points]
    min_dist_m = min(dists_m)

    within = [i for i, d in enumerate(dists_m) if d <= proximity_m]
    driver_arrived = bool(within)
    driver_arrival_time = None
    wait_duration_min = 0.0
    if driver_arrived:
        first_idx = within[0]
        last_idx = within[-1]
        driver_arrival_time = gps_points[first_idx][2]
        wait_duration_min = (
            gps_points[last_idx][2] - driver_arrival_time
        ).total_seconds() / 60.0

    cancellation_fee_valid = driver_arrived and wait_duration_min >= min_wait_min

    data = {
        "driver_arrived": driver_arrived,
        "driver_arrival_time": driver_arrival_time.isoformat()
        if driver_arrival_time is not None
        else None,
        "wait_duration_min": round(wait_duration_min, 2),
        "min_distance_to_pickup_m": round(min_dist_m, 1),
        "rider_reachable": rider_reachable,
        "cancellation_fee_valid": cancellation_fee_valid,
        "proximity_threshold_m": proximity_m,
        "min_wait_min": min_wait_min,
    }

    if not driver_arrived:
        supports = "rider"
        strength = min(1.0, 0.5 + min_dist_m / 1000.0)
        summary = f"Driver never reached the pickup point (closest {min_dist_m:.0f}m)."
    elif cancellation_fee_valid:
        supports = "driver"
        strength = min(1.0, 0.5 + wait_duration_min / 10.0)
        summary = f"Driver arrived and waited {wait_duration_min:.1f} min; cancellation fee is valid."
    else:
        supports = "neutral"
        strength = 0.3
        summary = "Driver arrived but did not meet the minimum wait threshold."

    return {"supports": supports, "strength": strength, "summary": summary, "data": data}


async def analyze_noshow(trip_id: int, session=None) -> EvidenceItem:
    async def _run(s):
        trip = (
            await s.execute(select(models.Trip).where(models.Trip.id == trip_id))
        ).scalar_one_or_none()
        if trip is None:
            raise ValueError(f"trip {trip_id} not found")

        # A completed trip (dropoff recorded) cannot be a no-show.
        if trip.dropoff_at is not None:
            result = {
                "supports": "neutral",
                "strength": 0.0,
                "summary": "Trip completed (drop-off recorded); not a no-show.",
                "data": {
                    "driver_arrived": True,
                    "driver_arrival_time": trip.pickup_at.isoformat()
                    if trip.pickup_at
                    else None,
                    "wait_duration_min": 0.0,
                    "min_distance_to_pickup_m": 0.0,
                    "rider_reachable": True,
                    "cancellation_fee_valid": False,
                    "proximity_threshold_m": settings.noshow_proximity_m,
                    "min_wait_min": settings.noshow_min_wait_min,
                    "trip_completed": True,
                    "fee": round(trip.cancellation_fee, 2),
                },
            }
            return result_to_evidence("noshow", trip_id, trip_id, result)

        pickup = (trip.optimal_route_polyline[0][0], trip.optimal_route_polyline[0][1])

        gps = (
            await s.execute(
                select(models.GpsPoint)
                .where(models.GpsPoint.trip_id == trip_id)
                .order_by(models.GpsPoint.ts)
            )
        ).scalars().all()
        pts = [(g.lat, g.lng, g.ts, g.speed_kmh) for g in gps]

        rider_msgs = (
            await s.execute(
                select(models.ChatMessage.id)
                .where(
                    models.ChatMessage.trip_id == trip_id,
                    models.ChatMessage.sender_id == trip.rider_id,
                )
            )
        ).scalars().all()
        rider_reachable = len(rider_msgs) > 0

        result = compute_noshow(
            pickup,
            pts,
            proximity_m=settings.noshow_proximity_m,
            min_wait_min=settings.noshow_min_wait_min,
            rider_reachable=rider_reachable,
        )
        result["data"]["fee"] = round(trip.cancellation_fee, 2)
        return result_to_evidence("noshow", trip_id, trip_id, result)

    if session is not None:
        return await _run(session)
    async with async_session_factory() as s:
        return await _run(s)
