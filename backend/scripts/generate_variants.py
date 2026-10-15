import asyncio
import copy
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings
from app.db.session import async_session_factory
from scripts.import_cases import _import_case

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
OFFICIAL_DIR = DATA_DIR / "official"
EVAL_DIR = DATA_DIR / "eval"

# Excess-distance fare rate (from DISP-001's fare_breakdown notes: $0.80/km).
PER_KM_FARE = 0.80

SECTION = {"route_deviation": "1", "no_show_charge": "2", "fare_dispute": "3"}


def parse_ts(value) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)


def load_official() -> dict[str, dict]:
    return {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted(OFFICIAL_DIR.glob("*.json"))}


# --------------------------------------------------------------------------
# Ground truth, written directly from Policy v2.1 (not the rules engine).
# --------------------------------------------------------------------------
def compute_expected(case: dict) -> dict:
    ticket = case["dispute_ticket"]
    dtype = ticket["dispute_type"]
    trip = case.get("trip_data") or {}
    rider = case.get("rider_profile") or {}
    driver = case.get("driver_profile") or {}

    fraud_flags = int(rider.get("fraud_flags") or 0) + int(driver.get("fraud_flags") or 0)

    amount = trip.get("actual_fare")
    if amount is None:
        actual_block = (case.get("fare_breakdown") or {}).get("actual_fare")
        amount = actual_block.get("total") if isinstance(actual_block, dict) else None
    if amount is None:
        amount = trip.get("cancellation_fee")
    amount = float(amount or 0.0)

    outcome = "no_refund"
    refund = 0.0
    route_over_2km = False

    if dtype == "route_deviation":
        deviation = trip.get("excess_distance_km")
        if deviation is None:
            deviation = float(trip.get("actual_distance_km") or 0.0) - float(trip.get("estimated_distance_km") or 0.0)
        deviation = float(deviation or 0.0)
        route_over_2km = deviation > settings.route_escalate_km
        traffic = bool((case.get("traffic_analysis") or {}).get("reroute_justified", False))
        notified = bool((case.get("chat_log_analysis") or {}).get("route_notification_sent", False))
        excess = float((case.get("fare_breakdown") or {}).get("excess_distance_fare") or 0.0)
        if deviation <= 1.0:
            outcome, refund = "no_refund", 0.0
        elif not traffic:
            outcome, refund = "full_refund", excess
        elif not notified:
            outcome, refund = "partial_refund", excess
        else:
            outcome, refund = "no_refund", 0.0

    elif dtype == "no_show_charge":
        fee = float(trip.get("cancellation_fee") or 5.0)
        driver_arrived = trip.get("driver_arrival_time") is not None or any(
            g.get("status") == "arrived" for g in (case.get("gps_telemetry") or [])
        )
        cancel = parse_ts(trip.get("cancellation_time"))
        messages = calls = 0
        for m in case.get("chat_logs") or []:
            if m.get("sender") != "driver":
                continue
            ts = parse_ts(m.get("timestamp"))
            if cancel is not None and ts is not None and ts > cancel:
                continue
            if m.get("type") == "call":
                calls += 1
            else:
                messages += 1
        contact_met = messages >= 1 and calls >= 1
        wait_start = parse_ts(trip.get("driver_wait_start")) or parse_ts(trip.get("scheduled_time"))
        wait_min = (cancel - wait_start).total_seconds() / 60.0 if (cancel and wait_start) else None
        free_wait = float((case.get("cancellation_policy") or {}).get("free_wait_time_min") or 5.0)
        if not driver_arrived:
            outcome, refund = "full_refund", fee
        elif not contact_met:
            outcome, refund = "full_refund", fee
        elif wait_min is not None and wait_min >= free_wait:
            outcome, refund = "no_refund", 0.0
        else:
            outcome, refund = "full_refund", fee

    elif dtype == "fare_dispute":
        surge_log = case.get("surge_pricing_log") or {}
        quote = surge_log.get("quote_time_surge")
        trip_surge = surge_log.get("trip_start_surge")
        surge_increased = quote is not None and trip_surge is not None and trip_surge > quote
        notified = surge_log.get("rider_notified", True)
        diff = trip.get("fare_difference")
        if diff is None:
            diff = (case.get("fare_breakdown") or {}).get("comparison", {}).get("total_difference")
        if diff is None:
            diff = float(trip.get("actual_fare") or 0.0) - float(trip.get("upfront_quote") or 0.0)
        diff = float(diff or 0.0)
        if surge_increased and not notified and diff > 0:
            outcome, refund = "full_refund", diff
        else:
            outcome, refund = "no_refund", 0.0

    safety = dtype == "safety_incident" or any(
        kw in (ticket.get("description") or "").lower() for kw in settings.safety_keywords
    )
    escalate = safety or amount > settings.escalation_high_value or route_over_2km or fraud_flags >= 1

    return {
        "external_id": ticket.get("dispute_id"),
        "section": SECTION.get(dtype, "?"),
        "outcome": outcome,
        "refund_amount": round(refund, 2),
        "escalate": escalate,
    }


# --------------------------------------------------------------------------
# Variant generation.
# --------------------------------------------------------------------------
def _variant(base: dict, name: str, mutate) -> dict:
    c = copy.deepcopy(base)
    c["dispute_ticket"]["dispute_id"] = name
    c["dispute_ticket"]["trip_id"] = f"TRIP-{name}"
    c["trip_data"]["trip_id"] = f"TRIP-{name}"
    c["trip_data"]["rider_id"] = f"R-{name}"
    c["trip_data"]["driver_id"] = f"D-{name}"
    c["rider_profile"]["rider_id"] = f"R-{name}"
    c["driver_profile"]["driver_id"] = f"D-{name}"
    mutate(c)
    return c


def _route(base, name, km, traffic, notified, fraud=0, fare=None):
    def mutate(c):
        c["trip_data"]["excess_distance_km"] = km
        c["fare_breakdown"]["excess_distance_fare"] = round(km * PER_KM_FARE, 2)
        c["chat_log_analysis"]["route_notification_sent"] = notified
        c["traffic_analysis"]["reroute_justified"] = traffic
        c["rider_profile"]["fraud_flags"] = fraud
        c["driver_profile"]["fraud_flags"] = 0
        if fare is not None:
            c["trip_data"]["actual_fare"] = fare
    return _variant(base, name, mutate)


def _rebuild_noshow_chat(case, messages, calls):
    trip = case["trip_data"]
    wait_start = parse_ts(trip["driver_wait_start"])
    cancel = parse_ts(trip["cancellation_time"])
    logs = []
    total = messages + calls
    for i in range(total):
        ts = wait_start + (cancel - wait_start) * (i + 1) / (total + 1)
        if i < messages:
            logs.append({"timestamp": ts.isoformat(), "sender": "driver", "type": "message", "content": f"Driver message {i + 1}"})
        else:
            logs.append({"timestamp": ts.isoformat(), "sender": "driver", "type": "call", "content": f"Outgoing call {i - messages + 1}"})
    logs.append({"timestamp": cancel.isoformat(), "sender": "system", "type": "system", "content": "Trip cancelled by driver."})
    case["chat_logs"] = logs


def _noshow(base, name, messages, calls, wait, fraud):
    def mutate(c):
        trip = c["trip_data"]
        wait_start = parse_ts(trip["driver_wait_start"])
        trip["cancellation_time"] = (wait_start + timedelta(minutes=wait)).isoformat()
        c["rider_profile"]["fraud_flags"] = fraud
        c["driver_profile"]["fraud_flags"] = 0
        _rebuild_noshow_chat(c, messages, calls)
    return _variant(base, name, mutate)


def _surge(base, name, notified, fraud=0, quote=None, actual=None, no_surge=False):
    def mutate(c):
        surge_log = c["surge_pricing_log"]
        surge_log["rider_notified"] = notified
        c["rider_profile"]["fraud_flags"] = fraud
        c["driver_profile"]["fraud_flags"] = 0
        if no_surge:
            surge_log["quote_time_surge"] = 1.0
            surge_log["trip_start_surge"] = 1.0
            c["fare_breakdown"]["actual_fare"]["surge_multiplier"] = 1.0
        if quote is not None and actual is not None:
            c["trip_data"]["upfront_quote"] = quote
            c["trip_data"]["actual_fare"] = actual
            c["trip_data"]["fare_difference"] = round(actual - quote, 2)
            c["fare_breakdown"]["upfront_quote"]["total"] = quote
            c["fare_breakdown"]["actual_fare"]["total"] = actual
            c["fare_breakdown"]["comparison"]["total_difference"] = round(actual - quote, 2)
            c["fare_breakdown"]["comparison"]["surge_amount_difference"] = round(actual - quote, 2)
    return _variant(base, name, mutate)


def make_variants(official: dict[str, dict]) -> list[dict]:
    route = official["DISP-001"]
    noshow = official["DISP-002"]
    surge = official["DISP-003"]

    variants = [
        # Route deviation (Sec 1)
        _route(route, "VAR-R01", km=0.5, traffic=True, notified=False),
        _route(route, "VAR-R02", km=1.5, traffic=False, notified=False),
        _route(route, "VAR-R03", km=1.5, traffic=True, notified=False),
        _route(route, "VAR-R04", km=1.5, traffic=True, notified=True),
        _route(route, "VAR-R05", km=2.5, traffic=True, notified=False),
        _route(route, "VAR-R06", km=1.5, traffic=False, notified=False, fraud=1),
        _route(route, "VAR-R07", km=1.5, traffic=True, notified=False, fare=60.0),
        _route(route, "VAR-R08", km=1.5, traffic=False, notified=False, fare=8.0),
        # No-show / cancellation fee (Sec 2)
        _noshow(noshow, "VAR-N01", messages=1, calls=1, wait=6, fraud=0),
        _noshow(noshow, "VAR-N02", messages=1, calls=0, wait=6, fraud=0),
        _noshow(noshow, "VAR-N03", messages=0, calls=0, wait=6, fraud=0),
        _noshow(noshow, "VAR-N04", messages=1, calls=1, wait=3, fraud=0),
        _noshow(noshow, "VAR-N05", messages=1, calls=1, wait=6, fraud=1),
        _noshow(noshow, "VAR-N06", messages=0, calls=0, wait=6, fraud=1),
        # Fare / surge (Sec 3)
        _surge(surge, "VAR-S01", notified=False),
        _surge(surge, "VAR-S02", notified=True),
        _surge(surge, "VAR-S03", notified=False, fraud=1),
        _surge(surge, "VAR-S04", notified=False, quote=12.0, actual=60.0),
        _surge(surge, "VAR-S05", notified=False, no_surge=True),
        _surge(surge, "VAR-S06", notified=False, quote=7.5, actual=8.0),
    ]
    return variants


async def _import_variants(session, variants) -> int:
    imported = 0
    for case in variants:
        if await _import_case(session, case):
            imported += 1
    await session.commit()
    return imported


def main() -> None:
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    official = load_official()

    golden = [official["DISP-001"], official["DISP-002"], official["DISP-003"]]
    variants = make_variants(official)

    expected = [compute_expected(c) for c in golden + variants]

    (EVAL_DIR / "variants.json").write_text(json.dumps(variants, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (EVAL_DIR / "expected.json").write_text(json.dumps(expected, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    async def _run():
        async with async_session_factory() as session:
            imported = await _import_variants(session, variants)
        print(f"Generated {len(variants)} variants (+3 golden) -> {EVAL_DIR}")
        print(f"Imported {imported} variant(s) into the DB.")

    asyncio.run(_run())


if __name__ == "__main__":
    main()
