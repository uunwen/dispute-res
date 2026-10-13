import math

from pyproj import Transformer
from shapely.geometry import LineString, Point
from sqlalchemy import select

from app.config import settings
from app.db import models
from app.db.session import async_session_factory
from app.evidence.base import result_to_evidence
from app.schemas.evidence import EvidenceItem

_TRANSFORMER = Transformer.from_crs("EPSG:4326", "EPSG:3414", always_xy=True)


def haversine_km(p, q):
    lat1, lng1 = p
    lat2, lng2 = q
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(
        math.radians(lat2)
    ) * math.sin(dlng / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _project(lat, lng):
    x, y = _TRANSFORMER.transform(lng, lat)
    return x, y


def compute_route_deviation(
    optimal_route,
    gps_points,
    *,
    buffer_m=100.0,
    estimated_distance_km=None,
    estimated_duration_min=None,
    stop_duration_min=2.0,
    traffic_speed_kmh=15.0,
    min_extra_km=2.0,
    min_fraction_outside=0.2,
):
    """Compute route-deviation evidence.

    gps_points is a list of ``(lat, lng, ts, speed_kmh)`` tuples sorted by time and
    optimal_route is a list of ``(lat, lng)`` tuples. Everything below is pure and
    deterministic: coordinates are projected to EPSG:3414 (SVY21, metres) with
    pyproj, the optimal route is buffered, and each GPS fix is classified inside or
    outside the buffer.
    """
    n = len(gps_points)
    if n == 0 or not optimal_route:
        return {
            "supports": "neutral",
            "strength": 0.0,
            "summary": "No GPS data available for route analysis.",
            "data": {"error": "no_data"},
        }

    line = LineString([_project(lat, lng) for lat, lng in optimal_route])
    buffer = line.buffer(buffer_m)

    is_outside = []
    for lat, lng, _ts, _spd in gps_points:
        is_outside.append(not buffer.contains(Point(*_project(lat, lng))))

    fraction_outside = sum(is_outside) / n

    actual_distance = 0.0
    for i in range(1, n):
        actual_distance += haversine_km(
            (gps_points[i - 1][0], gps_points[i - 1][1]),
            (gps_points[i][0], gps_points[i][1]),
        )

    if estimated_distance_km is None:
        optimal_distance = sum(
            haversine_km(optimal_route[i], optimal_route[i + 1])
            for i in range(len(optimal_route) - 1)
        )
    else:
        optimal_distance = estimated_distance_km

    extra_distance = actual_distance - optimal_distance

    longest_count = 0
    longest_duration_min = 0.0
    cur_count = 0
    run_first_ts = None
    run_last_ts = None
    for i in range(n):
        if is_outside[i]:
            if cur_count == 0:
                run_first_ts = gps_points[i][2]
            cur_count += 1
            run_last_ts = gps_points[i][2]
        else:
            if cur_count > longest_count and cur_count > 0:
                longest_count = cur_count
                longest_duration_min = (run_last_ts - run_first_ts).total_seconds() / 60.0
            cur_count = 0
    if cur_count > longest_count and cur_count > 0:
        longest_count = cur_count
        longest_duration_min = (run_last_ts - run_first_ts).total_seconds() / 60.0

    actual_duration_min = (gps_points[-1][2] - gps_points[0][2]).total_seconds() / 60.0
    duration_ratio = (
        actual_duration_min / estimated_duration_min if estimated_duration_min else None
    )

    stops = []
    in_stop = False
    stop_start = None
    stop_end = None
    for i in range(n):
        spd = gps_points[i][3]
        stopped = spd is not None and spd < 1.0
        if stopped:
            if not in_stop:
                in_stop = True
                stop_start = gps_points[i][2]
            stop_end = gps_points[i][2]
        elif in_stop:
            in_stop = False
            dur = (stop_end - stop_start).total_seconds() / 60.0
            if dur >= stop_duration_min:
                stops.append(dur)
    if in_stop:
        dur = (stop_end - stop_start).total_seconds() / 60.0
        if dur >= stop_duration_min:
            stops.append(dur)

    off_speeds = [
        gps_points[i][3]
        for i in range(n)
        if is_outside[i] and gps_points[i][3] is not None
    ]
    avg_speed_off_route = sum(off_speeds) / len(off_speeds) if off_speeds else 0.0

    first_off = next((i for i in range(n) if is_outside[i]), None)
    avg_speed_before = None
    if first_off is not None:
        window = [
            gps_points[i][3]
            for i in range(max(0, first_off - 6), first_off)
            if not is_outside[i] and gps_points[i][3] is not None
        ]
        if window:
            avg_speed_before = sum(window) / len(window)

    # Placeholder traffic heuristic (replace with a real traffic API later): if the
    # driver was moving slowly on the optimal route immediately before leaving it,
    # the deviation is more likely to be a legitimate detour around congestion.
    traffic_signal = (
        avg_speed_before is not None and avg_speed_before < traffic_speed_kmh
    )

    bad_faith = (
        fraction_outside >= min_fraction_outside
        and extra_distance >= min_extra_km
        and not traffic_signal
    )

    data = {
        "fraction_outside_buffer": round(fraction_outside, 4),
        "actual_distance_km": round(actual_distance, 3),
        "optimal_distance_km": round(optimal_distance, 3),
        "extra_distance_km": round(extra_distance, 3),
        "longest_off_route_stretch_min": round(longest_duration_min, 2),
        "longest_off_route_points": longest_count,
        "actual_duration_min": round(actual_duration_min, 2),
        "estimated_duration_min": round(estimated_duration_min, 2)
        if estimated_duration_min is not None
        else None,
        "duration_ratio": round(duration_ratio, 3) if duration_ratio is not None else None,
        "stops_gt_2min": len(stops),
        "avg_speed_off_route_kmh": round(avg_speed_off_route, 1),
        "avg_speed_before_deviation_kmh": round(avg_speed_before, 1)
        if avg_speed_before is not None
        else None,
        "traffic_signal": traffic_signal,
        "bad_faith_deviation": bad_faith,
    }

    if bad_faith:
        supports = "rider"
        strength = min(1.0, 0.4 + extra_distance / 5.0)
        summary = (
            f"Bad-faith route deviation: {extra_distance:.2f} km extra distance, "
            f"{fraction_outside * 100:.0f}% off-route, no traffic justification."
        )
    elif fraction_outside >= min_fraction_outside and traffic_signal:
        supports = "driver"
        strength = 0.6
        summary = "Detour appears justified by slow traffic on the optimal route."
    else:
        supports = "neutral"
        strength = 0.15
        summary = "No significant route deviation detected."

    return {"supports": supports, "strength": strength, "summary": summary, "data": data}


async def analyze_route_deviation(trip_id: int, session=None) -> EvidenceItem:
    async def _run(s):
        trip = (
            await s.execute(select(models.Trip).where(models.Trip.id == trip_id))
        ).scalar_one_or_none()
        if trip is None:
            raise ValueError(f"trip {trip_id} not found")

        gps = (
            await s.execute(
                select(models.GpsPoint)
                .where(models.GpsPoint.trip_id == trip_id)
                .order_by(models.GpsPoint.ts)
            )
        ).scalars().all()
        pts = [(g.lat, g.lng, g.ts, g.speed_kmh) for g in gps]
        route = [(p[0], p[1]) for p in (trip.optimal_route_polyline or [])]

        result = compute_route_deviation(
            route,
            pts,
            buffer_m=settings.route_buffer_m,
            estimated_distance_km=trip.estimated_distance_km,
            estimated_duration_min=trip.estimated_duration_min,
            stop_duration_min=settings.stop_duration_min,
            traffic_speed_kmh=settings.route_traffic_speed_kmh,
            min_extra_km=settings.route_min_extra_km,
            min_fraction_outside=settings.route_min_fraction_outside,
        )
        result["data"]["fare"] = round(trip.actual_fare, 2)
        result["data"]["total_km"] = round(trip.estimated_distance_km, 2)
        return result_to_evidence("route_deviation", trip_id, trip_id, result)

    if session is not None:
        return await _run(session)
    async with async_session_factory() as s:
        return await _run(s)
