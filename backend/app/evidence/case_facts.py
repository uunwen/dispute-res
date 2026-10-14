"""Deterministic case facts extracted from a trip's ``raw_case`` JSONB.

The official sample cases (DISP-001/002/003) carry rich structured data that the
normalized tables drop (call vs. message chat type, surge pricing logs, traffic
incident feed, cancellation policy block, etc.). This module recomputes the facts
the v2.1 rules depend on from that raw case, so advocates can cite them.

All facts are deterministic: no LLM, no math outside of pure Python.
"""

import re
from datetime import datetime

from sqlalchemy import select

from app.db import models
from app.db.session import async_session_factory
from app.evidence.base import result_to_evidence
from app.schemas.evidence import EvidenceItem

# Driver messages that, at or before a deviation, indicate the driver told the
# rider about a route change / traffic. Used only as a fallback when the case
# does not carry an explicit ``chat_log_analysis.route_notification_sent`` flag.
_ROUTE_NOTIFY_RE = re.compile(r"\b(route|rerout|traffic|jam|road|closed|detour|alternate)\b", re.IGNORECASE)


def parse_ts(value) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)


def _minutes_between(start, end) -> float | None:
    if start is None or end is None:
        return None
    return round((end - start).total_seconds() / 60.0, 2)


def compute_case_facts(raw_case: dict | None, *, driver_chat_messages: int = 0) -> dict:
    """Return the four deterministic fact groups as a flat dict.

    Keys are always present (with ``None`` / ``False`` / ``0`` defaults) so the
    rules engine never raises on a missing name.
    """
    if not raw_case:
        return {
            "driver_messages": driver_chat_messages,
            "driver_calls": 0,
            "contact_obligation_met": False,
            "wait_min": None,
            "free_wait_time_min": None,
            "no_show_threshold_min": None,
            "deviation_km": None,
            "surge_increased": False,
            "rider_notified": True,
            "surge_differential": 0.0,
            "booking_fee_surge_exempt": False,
            "deviation_notified": None,
            "traffic_justified": None,
            "excess_distance_fare": 0.0,
        }

    trip_data = raw_case.get("trip_data") or {}
    chat_logs = raw_case.get("chat_logs") or []
    cancellation_time = parse_ts(trip_data.get("cancellation_time"))

    # --- contact_attempts (Policy 2.3) ---
    driver_messages = 0
    driver_calls = 0
    for entry in chat_logs:
        if entry.get("sender") != "driver":
            continue
        ts = parse_ts(entry.get("timestamp"))
        if cancellation_time is not None and ts is not None and ts > cancellation_time:
            continue
        if entry.get("type") == "call":
            driver_calls += 1
        else:
            driver_messages += 1
    contact_obligation_met = driver_messages >= 1 and driver_calls >= 1

    # --- wait per Sec 2.1 (from scheduled pickup / driver wait start) ---
    wait_start = parse_ts(trip_data.get("driver_wait_start")) or parse_ts(trip_data.get("scheduled_time"))
    wait_min = _minutes_between(wait_start, cancellation_time)
    cancellation_policy = raw_case.get("cancellation_policy") or {}
    free_wait = cancellation_policy.get("free_wait_time_min")
    no_show_threshold = cancellation_policy.get("no_show_threshold_min")

    # --- surge notification (Policy 3.3 / 3.5) ---
    surge_log = raw_case.get("surge_pricing_log") or {}
    quote_surge = surge_log.get("quote_time_surge")
    trip_surge = surge_log.get("trip_start_surge")
    surge_increased = (
        quote_surge is not None and trip_surge is not None and trip_surge > quote_surge
    )
    rider_notified = surge_log.get("rider_notified")
    if rider_notified is None:
        rider_notified = True  # no surge log -> treat as nothing to notify

    fare = raw_case.get("fare_breakdown") or {}
    comparison = fare.get("comparison") or {}
    quote_total = (fare.get("upfront_quote") or {}).get("total")
    if quote_total is None:
        quote_total = trip_data.get("upfront_quote")
    actual_total = (fare.get("actual_fare") or {}).get("total")
    if actual_total is None:
        actual_total = trip_data.get("actual_fare")
    if quote_total is not None and actual_total is not None:
        surge_differential = round(float(actual_total) - float(quote_total), 2)
    else:
        surge_differential = float(comparison.get("total_difference") or 0.0)
    booking_fee_surge_exempt = bool(comparison.get("booking_fee_surge_exempt", False))

    # --- deviation notification (Policy 1.2) ---
    chat_analysis = raw_case.get("chat_log_analysis") or {}
    deviation_notified = chat_analysis.get("route_notification_sent")
    if deviation_notified is None:
        deviation_notified = any(
            entry.get("sender") == "driver" and _ROUTE_NOTIFY_RE.search(entry.get("message") or entry.get("content") or "")
            for entry in chat_logs
        )

    traffic_analysis = raw_case.get("traffic_analysis") or {}
    traffic_justified = traffic_analysis.get("reroute_justified")

    excess_distance_fare = float(fare.get("excess_distance_fare") or 0.0)

    # Authoritative deviation distance from the case (meter/odometer), which the
    # sparse GPS telemetry alone can under-count.
    deviation_km = trip_data.get("excess_distance_km")
    if deviation_km is None:
        actual_km = trip_data.get("actual_distance_km")
        estimated_km = trip_data.get("estimated_distance_km")
        if actual_km is not None and estimated_km is not None:
            deviation_km = round(float(actual_km) - float(estimated_km), 3)
    deviation_km = float(deviation_km) if deviation_km is not None else None

    return {
        "driver_messages": driver_messages,
        "driver_calls": driver_calls,
        "contact_obligation_met": contact_obligation_met,
        "wait_min": wait_min,
        "free_wait_time_min": free_wait,
        "no_show_threshold_min": no_show_threshold,
        "deviation_km": deviation_km,
        "surge_increased": surge_increased,
        "rider_notified": rider_notified,
        "surge_differential": surge_differential,
        "booking_fee_surge_exempt": booking_fee_surge_exempt,
        "deviation_notified": deviation_notified,
        "traffic_justified": traffic_justified,
        "excess_distance_fare": excess_distance_fare,
    }


def _summary(data: dict) -> str:
    parts = [
        f"contact: {data['driver_messages']} msg / {data['driver_calls']} call "
        f"(obligation {'met' if data['contact_obligation_met'] else 'not met'})",
        f"wait: {data['wait_min']} min",
        f"surge: increased={data['surge_increased']} notified={data['rider_notified']} "
        f"diff={data['surge_differential']}",
        f"deviation: notified={data['deviation_notified']} traffic={data['traffic_justified']}",
    ]
    return "case_facts " + " | ".join(parts)


async def analyze_case_facts(trip_id: int, session=None) -> EvidenceItem:
    async def _run(s):
        trip = (
            await s.execute(select(models.Trip).where(models.Trip.id == trip_id))
        ).scalar_one_or_none()
        if trip is None:
            raise ValueError(f"trip {trip_id} not found")

        driver_messages = 0
        if trip.raw_case is None:
            driver_messages = (
                await s.execute(
                    select(models.ChatMessage.id).where(
                        models.ChatMessage.trip_id == trip_id,
                        models.ChatMessage.sender_id == trip.driver_id,
                    )
                )
            ).scalars().all()
            driver_messages = len(driver_messages)

        data = compute_case_facts(trip.raw_case, driver_chat_messages=driver_messages)
        result = {
            "supports": "neutral",
            "strength": 1.0 if trip.raw_case else 0.0,
            "summary": _summary(data),
            "data": data,
        }
        return result_to_evidence("case_facts", trip_id, trip_id, result)

    if session is not None:
        return await _run(session)
    async with async_session_factory() as s:
        return await _run(s)
