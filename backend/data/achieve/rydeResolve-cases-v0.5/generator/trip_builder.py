"""Completed (or driver-ended) trips for the property damage and safety categories (v0.5).

A trip follows the app's planned road route (lib.road_via). The car's speed is set per stretch of the
route, so every GPS ping's position, timestamp and speed agree with each other. Safety cases carry the
posted speed limit on every ping (`speed_limit_kmh`); other cases leave it null.

Property damage cases add the driver's cleaning claim (`trip_data.damage_claim`) and the photos and
receipt (`attachments`). Each photo's `simulated_vision_analysis` is the output an image-analysis model
would give. There is no real image file; this is said inside every photo record.
"""
import hashlib
from datetime import timedelta

from lib import (PARAMS, POLICY_VERSION, T, fare, hav, iso, latlng, lerp, money, move, place, ppos,
                 road_via, rng_for)

DMG = PARAMS["damage"]
CITY, EXPRESSWAY = 50, 90
DEFAULT_PROFILE = ((0.0, 0.18, 32, CITY), (0.18, 0.84, 66, EXPRESSWAY), (0.84, 1.0, 30, CITY))
SHORT_TRIP_PROFILE = ((0.0, 1.0, 31, CITY),)  # under 8 km: town roads only
SHORT_TRIP_KM = 8.0
VISION_NOTE = ("Simulated output of an image-analysis model, generated for this test case. "
               "No image file exists.")


def _m(minutes):
    return timedelta(seconds=round(minutes * 60))


def _plate(vehicle):
    return vehicle[vehicle.index("(") + 1:vehicle.index(")")]


def _point_at(pts, cum, d):
    """Position at distance d (km) along the polyline pts with cumulative lengths cum."""
    for i in range(len(pts) - 1):
        if d <= cum[i + 1] or i == len(pts) - 2:
            seg = cum[i + 1] - cum[i]
            f = 0 if seg == 0 else min(1.0, max(0.0, (d - cum[i]) / seg))
            return lerp(pts[i], pts[i + 1], f)


def _hash(cid, n):
    return "sha256:" + hashlib.sha256(f"{cid}-{n}".encode()).hexdigest()[:40]


def build_trip(cid, *, category, title, pickup, dropoff, t0, rider, driver, desc, filed_by="rider",
               profile=None, overrides=None, end_at=None, end_reason=None, chat=(),
               extra_events=(), filed_after_min=None, wait_pick=6, limits=False, damage=None,
               next_trip_after_min=None, planned_speed=38, seed=None, at_pickup_min=1.0):
    """
    profile: stretches (f_from, f_to, nominal_kmh, limit_kmh) as fractions of the planned route.
    overrides: {minute_after_trip_start: (exact_kmh, expected_limit)} for pings whose speed must be exact
               (the builder checks the limit really is the expected one at that point).
    end_at: fraction of the route where the driver ended the trip early (None = completed).
    end_reason: reason the driver selected when ending early (None = no reason given).
    chat / extra_events: (minutes after trip start, ...).
    limits: put the posted speed limit on every ping (safety cases).
    damage: property damage claim, see pd_cases.py.
    """
    rng = rng_for(seed or cid)  # a consistency variant reuses its source case's seed: identical trip
    overrides = overrides or {}
    t0 = T(t0)
    a, b = ppos(pickup), ppos(dropoff)
    pts = [a, road_via(pickup, dropoff), b]
    cum = [0.0]
    for i in range(len(pts) - 1):
        cum.append(cum[-1] + hav(pts[i], pts[i + 1]))
    planned_km = cum[-1]
    planned_min = planned_km / planned_speed * 60
    if profile is None:
        profile = SHORT_TRIP_PROFILE if planned_km < SHORT_TRIP_KM else DEFAULT_PROFILE
    stop_km = planned_km * (end_at if end_at is not None else 1.0)
    t_start = t0 + _m(wait_pick)

    def stretch(d):
        f = d / planned_km
        for f0, f1, kmh, lim in profile:
            if f0 <= f < f1 or (f1 == 1.0 and f >= f1):
                return kmh, lim
        return profile[-1][2], profile[-1][3]

    gps, d, minute, total_min = [], 0.0, 0, None
    while total_min is None:
        nominal, lim = stretch(d)
        if minute in overrides:
            kmh, want_lim = overrides[minute]
            if want_lim != lim:
                raise ValueError(f"{cid}: override at minute {minute} falls where the limit is {lim}, "
                                 f"not {want_lim}")
        else:
            kmh = max(5, nominal + rng.randint(-3, 3))
        p = move(_point_at(pts, cum, d), rng.uniform(0, 6), rng.uniform(0, 360))
        gps.append({"timestamp": iso(t_start + _m(minute)), **latlng(p), "speed_kmh": kmh,
                    "accuracy_m": round(rng.uniform(4, 10), 1), "status": "on_trip",
                    "speed_limit_kmh": lim if limits else None})
        step = kmh / 60.0
        if d + step >= stop_km - 1e-9:  # the last stretch is shorter than a full minute
            total_min = round(minute + max(0.2, (stop_km - d) / step), 1)
        d += step
        minute += 1
    end_pos = _point_at(pts, cum, stop_km)
    t_end = t_start + _m(total_min)
    gps.append({"timestamp": iso(t_end), **latlng(end_pos), "speed_kmh": 0,
                "accuracy_m": round(rng.uniform(4, 10), 1),
                "status": "completed" if end_at is None else "ended_early",
                "speed_limit_kmh": stretch(min(stop_km, planned_km - 1e-6))[1] if limits else None})

    est = fare(planned_km, planned_min)
    charged = fare(stop_km, total_min)
    charged["promo_code"] = None
    charged["erp_gantries_passed"] = []
    charged["destination_change_fee"] = 0.0

    ev = []

    def add(t, typ, details):
        ev.append({"timestamp": iso(t), "event_type": typ, "details": details})

    trip_id = "TRIP-" + cid
    add(t0, "booking_confirmed",
        f"Rider {rider['rider_id']} booked trip {trip_id} from {place(pickup)['name']} to "
        f"{place(dropoff)['name']}. Upfront estimate ${est['total']:.2f} for planned route "
        f"{planned_km:.1f} km / {planned_min:.0f} min. Surge x1.0.")
    add(t0 + timedelta(seconds=15), "driver_assigned",
        f"Driver {driver['driver_id']} ({driver['name']}, {driver['vehicle']}) assigned.")
    add(t_start - _m(at_pickup_min), "driver_arrived", "Driver GPS within 9 m of pickup point.")
    add(t_start, "trip_started", "Rider boarded. Trip meter started.")
    for (mins, typ, details) in extra_events:
        add(t_start + _m(mins), typ, details)
    if end_at is None:
        add(t_end, "trip_completed",
            f"Trip completed at {place(dropoff)['name']}. Meter distance {stop_km:.2f} km, "
            f"duration {total_min:.1f} min.")
    else:
        reason = end_reason or "none given"
        add(t_end, "trip_ended_early",
            f"Driver ended the trip before the destination. Reason selected: {reason}. Meter distance "
            f"{stop_km:.2f} km, duration {total_min:.1f} min. Rider charged for the distance travelled.")
    add(t_end + timedelta(seconds=20), "payment_captured",
        f"${charged['total']:.2f} charged to rider payment method ({rider['payment_method']}).")
    if next_trip_after_min is not None:
        add(t_end + _m(next_trip_after_min), "driver_next_trip_started",
            f"Driver {driver['driver_id']} started the next trip (TRIP-{cid}-NEXT) with another rider.")

    attachments, claim, claim_t = [], None, None
    if damage:
        plate = _plate(driver["vehicle"])
        claim_t = t_end + _m(damage["submitted_after_min"])
        claim_id = "CLM-" + cid.replace("DISP-T-", "").replace("PREC-", "P")
        n = 0
        for ph in damage["photos"]:
            n += 1
            cap = t_start + _m(ph["from_start"]) if "from_start" in ph else t_end + _m(ph["after_min"])
            shows = ph.get("plate", False)
            plate_read = plate if shows is True else (shows or None)
            loc = None
            # a phone photo carries a location only when taken at the car soon after the trip
            if ph.get("located", "from_start" not in ph and 0 <= ph["after_min"] <= 30):
                loc = latlng(move(end_pos, rng.uniform(5, 40), rng.uniform(0, 360)), 5)
            attachments.append({
                "attachment_id": f"ATT-{claim_id}-{n}", "attachment_type": "photo",
                "uploaded_by": "driver", "uploaded_at": iso(claim_t), "captured_at": iso(cap),
                "location": loc, "file_hash": _hash(cid, n),
                "simulated_vision_analysis": {
                    "note": VISION_NOTE, "description": ph["description"],
                    "mess_type": ph["mess_type"], "severity": ph["severity"],
                    "plate_read": plate_read, "interior_matches_vehicle_model": ph.get("interior_match", True),
                    "ai_generated_likelihood": ph.get("ai", round(rng.uniform(0.01, 0.06), 2)),
                    "duplicate_of": ph.get("duplicate_of"),
                },
                "receipt_details": None,
            })
        rc = damage.get("receipt")
        if rc:
            n += 1
            date = (t_end + timedelta(days=rc.get("date_offset_days", 0))).date().isoformat()
            attachments.append({
                "attachment_id": f"ATT-{claim_id}-{n}", "attachment_type": "receipt",
                "uploaded_by": "driver", "uploaded_at": iso(claim_t),
                "captured_at": iso(claim_t - _m(rc.get("scanned_before_claim_min", 25))),
                "location": None, "file_hash": _hash(cid, n),
                "simulated_vision_analysis": None,
                "receipt_details": {
                    "company_name": rc.get("company", "SparkleCar Interior Cleaning Pte Ltd"),
                    "uen": rc.get("uen", "201912345K"),
                    "address": rc.get("address", "10 Ubi Crescent, #01-23, Singapore 408564"),
                    "contact_number": rc.get("contact", "+65 6745 1122"),
                    "service_description": rc["service"],
                    "professional_cleaning": rc.get("professional", True),
                    "cleaning_date": date,
                    "car_plate": plate if rc.get("plate", True) is True else rc.get("plate"),
                    "amount": money(rc["amount"]),
                    "signed": rc.get("signed", True),
                    "company_stamp": rc.get("stamped", True),
                },
            })
        claim = {
            "claim_id": claim_id, "submitted_at": iso(claim_t),
            "mess_type_claimed": damage["claimed_type"], "amount_claimed": money(damage["amount_claimed"]),
            "attachment_ids": [x["attachment_id"] for x in attachments],
            "status": damage["status"], "amount_charged": money(damage.get("amount_charged", 0.0)),
        }
        add(claim_t, "cleaning_claim_submitted",
            f"Driver {driver['driver_id']} submitted cleaning claim {claim_id} for {damage['claimed_type']}: "
            f"${damage['amount_claimed']:.2f} with {len(attachments)} attachment(s).")
        if damage["status"] == "charged":
            add(claim_t + timedelta(hours=26), "cleaning_fee_charged",
                f"Cleaning fee ${damage['amount_charged']:.2f} for claim {claim_id} charged to rider payment "
                f"method ({rider['payment_method']}).")
    ev.sort(key=lambda e: e["timestamp"])

    chats = []
    for c in chat:
        mins, sender, typ, content = c[:4]
        chats.append({"timestamp": iso(t_start + _m(mins)), "sender": sender, "type": typ, "content": content})
    chats.sort(key=lambda c: c["timestamp"])

    if filed_after_min is not None:
        filed = t_end + _m(filed_after_min)
    elif damage and damage["status"] == "charged":
        filed = claim_t + timedelta(hours=26) + _m(rng.randint(60, 30 * 60))
    elif damage:
        filed = claim_t + _m(rng.randint(5, 90))
    else:
        filed = t_end + _m(rng.randint(30, 20 * 60))

    case = {
        "dispute_ticket": {"dispute_id": cid, "trip_id": trip_id, "filed_by": filed_by,
                           "dispute_type": category, "description": desc, "filed_at": iso(filed),
                           "status": "open"},
        "rider_profile": rider,
        "driver_profile": driver,
        "trip_data": {
            "trip_id": trip_id, "rider_id": rider["rider_id"], "driver_id": driver["driver_id"],
            "pickup_location": place(pickup), "dropoff_location": place(dropoff),
            "booked_at": iso(t0), "trip_start": iso(t_start), "trip_end": iso(t_end),
            "trip_completed": end_at is None,
            "planned_route": {"distance_km": round(planned_km, 2), "duration_min": round(planned_min, 1),
                              "waypoints": [latlng(p, 5) for p in pts], "erp_gantries": []},
            "upfront_estimate": est,
            "damage_claim": claim,
        },
        "fare_breakdown": charged,
        "gps_telemetry": gps,
        "chat_logs": chats,
        "app_events": ev,
        "attachments": attachments,
        "policy_ref": POLICY_VERSION,
    }
    over = [g["speed_kmh"] - g["speed_limit_kmh"] for g in gps if g["speed_limit_kmh"]]
    metrics = {
        "planned_km": round(planned_km, 2), "actual_km": round(stop_km, 2), "actual_min": total_min,
        "estimate": est["total"], "charged": charged["total"],
        "max_over_limit_kmh": max(over) if over else None,
        "ended_early": end_at is not None,
        "claim_submitted_after_h": round(damage["submitted_after_min"] / 60, 1) if damage else None,
    }
    return case, metrics
