"""Builders that turn a compact scenario spec into a full DISP-002-style case.

Times in specs are minutes (floats). For no-show cases most times are relative
to the driver's arrival EVENT, because that is how people reason about waits.
"""
from datetime import timedelta

from lib import (NS_POL, POLICY_VERSION, PROFILES, RD_POL, OnLine, Path, T, fare, hav, iso, latlng, lerp, move,
                 money, on_land, place, poly_km, ppos, rng_for, road_via)


def _m(minutes):
    return timedelta(seconds=round(minutes * 60))


# --------------------------------------------------------------------------
# No-show, cancellation and waiting-fee cases
# --------------------------------------------------------------------------

def policy_block(profile):
    """The cancellation_policy block a case carries (copied from policy/params.json)."""
    return dict(PROFILES[profile])


def build_ns(cid, *, title, pickup, dropoff, t0, eta, rider, driver, desc,
             profile="ryde_published", mode="driver_cancel", trip_type="on_demand",
             filed_by="rider", arrive=None, stop=(6, 0), event=None, cancel=4.5,
             rider_cancel=None, board=None, ride_min=12, approach=None, chat=(),
             rider_pings=None, extra_events=(), gps_mode="normal", gap=None,
             filed_after_min=None, filed_after_days=None, pin_note=None,
             cancel_reason="rider_no_show", fee=None, waiting_charged=None,
             event_details=None, payment="captured", no_tap=False, chat_at_t0=False, no_fee_note=None):
    """
    All minute values are measured from t0 (the match time) unless stated.
    mode          : "driver_cancel" (driver cancels as no-show), "rider_cancel" (rider cancels in the app),
                    "boarded" (rider boards late and the trip completes: waiting-fee disputes)
    arrive        : minutes after t0 when the driver's GPS reaches `stop`
    stop          : (metres from pin, bearing) where the driver parks
    event         : {"at": minutes after t0, "method": "manual"|"auto"}; default a manual tap at `arrive`
    no_tap        : the driver never tapped "I'm Here" (only meaningful for rider_cancel)
    cancel        : (driver_cancel) minutes after the tap when the driver cancels
    rider_cancel  : (rider_cancel) minutes after t0 when the rider cancels
    board         : (boarded) minutes after the tap when the rider boards
    approach      : list of (minutes after t0, metres from the parked point, speed km/h) before arrival
    chat          : list of (minutes after the tap, sender, type, content[, extras]); with chat_at_t0
                    the minutes are measured from t0 instead
    rider_pings   : list of (minutes after t0, metres from pin, bearing, accuracy_m)
    fee           : whether the app charged the cancellation fee (default follows the app's own timer)
    waiting_charged: amount charged as waiting fee in "boarded" mode (default follows the app's timer)
    """
    rng = rng_for(cid)
    t0 = T(t0)
    pol = policy_block(profile)
    free = pol["free_wait_time_min"]
    thr = pol["no_show_threshold_min"]
    arrive = eta if arrive is None else arrive
    pin = ppos(pickup)
    drop = ppos(dropoff)
    stop_pt = pin if stop[0] == 0 else move(pin, stop[0], stop[1])
    # approach from a direction that stays on land (an audit found approach pings in the sea)
    for _ in range(200):
        bearing_in = rng.uniform(0, 360)
        if all(on_land(move(stop_pt, d, bearing_in)) for d in (600, 1500, 2500, 3500)):
            break

    tapped = not no_tap
    event = event or {"at": arrive, "method": "manual"}
    t_event = t0 + _m(event["at"]) if tapped else None
    t_arrive = t0 + _m(arrive)
    t_sched = t0 + _m(eta)
    matched_at = t0 + timedelta(seconds=15)

    if mode == "driver_cancel":
        t_end = t_event + _m(cancel)
    elif mode == "rider_cancel":
        t_end = t0 + _m(rider_cancel)
    elif mode == "boarded":
        t_board = t_event + _m(board)
        t_end = t_board + _m(ride_min)
    else:
        raise ValueError(mode)
    t_wait_end = (t_event + _m(board)) if (mode == "boarded" and tapped) else t_end

    if approach is None:
        # speeds match the distance covered between pings (city traffic, about 15-25 km/h)
        approach = [(arrive - 12, 3200, 22), (arrive - 9, 2300, 19), (arrive - 6, 1400, 17),
                    (arrive - 3, 600, 14), (arrive - 1, 150, 9)]
        approach = [a for a in approach if a[0] > 0.5]

    def status_at(t):
        if mode == "boarded" and t >= t_wait_end:
            return "completed" if t >= t_end else "on_trip"
        if mode in ("driver_cancel", "rider_cancel") and t >= t_end:
            return "cancelled"
        if tapped and t >= t_event:
            return "arrived" if t == t_event else "waiting"
        return "en_route"

    gps = []
    for (mins, dist, speed) in approach:
        t = t0 + _m(mins)
        if t > t_end:
            continue
        p = move(stop_pt, dist, bearing_in) if dist else stop_pt
        if gps_mode != "spoof" and speed <= NS_POL["stationary_max_kmh"]:
            p = move(p, rng.uniform(0.5, 3), rng.uniform(0, 360))  # a parked car's GPS still jitters
        gps.append({"timestamp": iso(t), **latlng(p), "speed_kmh": speed,
                    "accuracy_m": 1.0 if gps_mode == "spoof" else round(rng.uniform(4, 11), 1),
                    "status": status_at(t)})

    # stationary pings once a minute from arrival to the end of the wait (if the driver got there)
    if arrive is not None and t_arrive <= t_wait_end:
        t = t_arrive
        while t <= t_wait_end:
            if gps_mode == "spoof":
                p, acc = stop_pt, 1.0
            else:
                p = move(stop_pt, rng.uniform(0, 4), rng.uniform(0, 360))
                acc = round(rng.uniform(4, 9), 1)
            gps.append({"timestamp": iso(t), **latlng(p), "speed_kmh": 0, "accuracy_m": acc,
                        "status": status_at(t)})
            nxt = t + timedelta(seconds=60)
            if t < t_wait_end < nxt:
                nxt = t_wait_end
            if nxt == t:
                break
            t = nxt

    if mode == "boarded":
        n = max(int(ride_min // 2), 1)
        for i in range(1, n + 1):
            f = i / n
            t = t_wait_end + _m(ride_min * f)
            p = lerp(stop_pt, drop, f)
            gps.append({"timestamp": iso(t), **latlng(p), "speed_kmh": 0 if f == 1 else round(rng.uniform(28, 42)),
                        "accuracy_m": round(rng.uniform(4, 9), 1), "status": status_at(t)})

    if gap:
        g0, g1 = t0 + _m(gap[0]), t0 + _m(gap[1])
        gps = [g for g in gps if not (g0 <= T(g["timestamp"][:19]) <= g1)]
    gps.sort(key=lambda g: g["timestamp"])

    # ---- app events ----
    ev = []

    def add(t, typ, details):
        ev.append({"timestamp": iso(t), "event_type": typ, "details": details})

    trip_id = "TRIP-" + cid
    adv = trip_type == "advance"
    t_booked = t0 - timedelta(hours=3) if adv else t0
    add(t_booked, "booking_confirmed",
        f"Rider {rider['rider_id']} booked trip {trip_id} from {place(pickup)['name']} to "
        f"{place(dropoff)['name']}. "
        + (f"Advance booking for pickup at {t_sched.strftime('%H:%M')}. " if adv
           else f"On-demand booking. Estimated pickup {t_sched.strftime('%H:%M')}. ")
        + "Pickup pin set by rider." + (f" {pin_note}" if pin_note else ""))
    add(matched_at, "driver_assigned",
        f"Driver {driver['driver_id']} ({driver['name']}, {driver['vehicle']}) "
        + (f"accepted the advance booking. Scheduled pickup {t_sched.strftime('%H:%M')}." if adv
           else f"matched. ETA {eta} min."))
    add(t0 + timedelta(seconds=20), "driver_en_route",
        "Driver started navigating to pickup location. Live tracking enabled.")

    d_event_m = None
    if tapped:
        d_event_m = round(hav(pin, _pos_at(gps, t_event, stop_pt)) * 1000)
        if event_details:
            add(t_event, "driver_arrived", event_details)
        elif event["method"] == "auto":
            add(t_event, "driver_arrived",
                f"Driver GPS within {max(d_event_m, 1)} m of pickup point. Speed 0 km/h. Arrival auto-confirmed.")
        else:
            add(t_event, "driver_arrived",
                f"Driver tapped 'I'm Here'. Driver GPS {d_event_m} m from pickup point at time of tap.")
        add(t_event + timedelta(seconds=5), "rider_notified",
            "Push notification + in-app alert sent to rider: 'Your driver has arrived.'")
        t_exp = t_event + _m(thr)
        add(t_event, "wait_timer_started",
            f"Wait timer started at the arrival event. The no-show threshold ({thr} min) is reached at "
            f"{t_exp.strftime('%H:%M:%S')}.")
        if t_exp < t_wait_end:
            add(t_exp, "wait_timer_threshold_reached",
                f"Wait timer reached {thr} min. Rider had not boarded.")

    tap_wait = (t_wait_end - t_event).total_seconds() / 60 if tapped else 0.0
    cancelled_by = {"driver_cancel": "driver", "rider_cancel": "rider", "boarded": None}[mode]
    fee_amt = pol["cancellation_fee_after_wait"]

    # chat
    t_chat = t0 if (chat_at_t0 or not tapped) else t_event
    chats = []
    for c in chat:
        mins, sender, typ, content = c[:4]
        extras = c[4] if len(c) > 4 else {}
        t = t_chat + _m(mins)
        item = {"timestamp": iso(t), "sender": sender, "type": typ, "content": content}
        item.update(extras)
        chats.append(item)
        if typ == "call":
            who = "Driver" if sender == "driver" else "Rider"
            add(t, f"{sender}_called_{'rider' if sender == 'driver' else 'driver'}",
                f"{who} initiated in-app call. {content}")
    for (mins, typ, details) in extra_events:
        add(t0 + _m(mins), typ, details)

    fee_applied, wait_fee = False, 0.0
    if mode == "driver_cancel":
        # The mock app charges the fee whenever the driver cancels with reason rider_no_show (policy NS-10).
        fee_applied = fee if fee is not None else (cancel_reason == "rider_no_show")
        if fee_applied and payment == "declined":
            add(t_end, "payment_declined",
                f"Driver cancelled with reason {cancel_reason}. Cancellation fee ${fee_amt:.2f} could not be "
                f"collected: rider payment method ({rider['payment_method']}) declined.")
            sys_msg = f"Trip cancelled by driver. Reason: {cancel_reason}. Cancellation fee could not be collected."
        elif fee_applied:
            add(t_end, "cancellation_fee_applied",
                f"Driver cancelled with reason {cancel_reason} at {tap_wait:.1f} min on the wait timer. "
                f"${fee_amt:.2f} cancellation fee charged to rider payment method "
                f"({rider['payment_method']}). The app charges the fee whenever a driver cancels with this "
                "reason; validity is checked only if the rider disputes it.")
            sys_msg = (f"Trip cancelled by driver. Reason: {cancel_reason}. Cancellation fee of "
                       f"${fee_amt:.2f} applied.")
        else:
            add(t_end, "trip_cancelled_by_driver",
                f"Driver cancelled with reason {cancel_reason}. No cancellation fee applied.")
            sys_msg = f"Trip cancelled by driver. Reason: {cancel_reason}. No cancellation fee applied."
        cancel_reason_out = cancel_reason
    elif mode == "rider_cancel":
        since_match = (t_end - matched_at).total_seconds() / 60
        if adv:
            in_window = (t_end <= t_sched - _m(pol.get("advance_free_before_min", 15))
                         or since_match <= free)
        else:
            in_window = since_match <= free
        fee_applied = fee if fee is not None else (not in_window)
        if fee_applied:
            add(t_end, "trip_cancelled_by_rider",
                f"Rider cancelled the trip in-app {since_match:.1f} min after matching. ${fee_amt:.2f} "
                f"cancellation fee charged to rider payment method ({rider['payment_method']}).")
            sys_msg = f"Trip cancelled by rider. Cancellation fee of ${fee_amt:.2f} applied."
        else:
            add(t_end, "trip_cancelled_by_rider",
                f"Rider cancelled the trip in-app {since_match:.1f} min after matching. No cancellation fee "
                "applied." + (f" {no_fee_note}" if no_fee_note else ""))
            sys_msg = "Trip cancelled by rider. No cancellation fee applied."
        cancel_reason_out = "rider_cancelled"
    else:
        wf = pol.get("waiting_fee", 5.0)
        wait_fee = waiting_charged if waiting_charged is not None else (wf if tap_wait > thr else 0.0)
        add(t_wait_end, "trip_started", "Rider boarded. Trip meter started.")
        add(t_end, "trip_completed", f"Trip completed at {place(dropoff)['name']}.")
        if wait_fee:
            add(t_end + timedelta(seconds=10), "waiting_fee_applied",
                f"Waiting time fee ${wait_fee:.2f} added to fare. Driver tapped 'I'm Here' "
                f"{tap_wait:.1f} min before the rider boarded.")
        add(t_end + timedelta(seconds=20), "payment_captured",
            f"Fare and fees charged to rider payment method ({rider['payment_method']}).")
        sys_msg = None
        cancel_reason_out = None
    if mode != "boarded":
        add(t_end + timedelta(seconds=5), "driver_released",
            f"Driver {driver['driver_id']} released from trip. Trip status: cancelled ({cancel_reason_out}).")
        chats.append({"timestamp": iso(t_end), "sender": "system", "type": "system", "content": sys_msg})
    chats.sort(key=lambda c: c["timestamp"])
    ev.sort(key=lambda e: e["timestamp"])

    rloc = None
    if rider_pings:
        rloc = []
        for (mins, dist, br, acc) in rider_pings:
            p = pin if dist == 0 else move(pin, dist, br)
            # phones jitter: never the same coordinate twice, never a round distance
            p = move(p, rng.uniform(1, 5), rng.uniform(0, 360))
            rloc.append({"timestamp": iso(t0 + _m(mins)), **latlng(p),
                         "accuracy_m": round(max(3.0, acc + rng.uniform(-2, 2)), 1)})

    if filed_after_days is not None:
        filed_at = t_end + timedelta(days=filed_after_days, minutes=rng.randint(60, 600))
    else:
        filed_at = t_end + _m(filed_after_min if filed_after_min is not None else rng.randint(15, 600))

    case = {
        "dispute_ticket": {
            "dispute_id": cid, "trip_id": trip_id, "filed_by": filed_by,
            "dispute_type": "no_show_charge", "description": desc,
            "filed_at": iso(filed_at), "status": "open",
        },
        "rider_profile": rider,
        "driver_profile": driver,
        "trip_data": {
            "trip_id": trip_id, "rider_id": rider["rider_id"], "driver_id": driver["driver_id"],
            "pickup_location": place(pickup), "dropoff_location": place(dropoff),
            # Field names up to "cancellation_reason" follow Ryde's DISP-002 sample.
            "scheduled_time": iso(t_sched),
            "driver_arrival_time": iso(t_event) if tapped else None,
            "driver_wait_start": iso(t_event) if tapped else None,
            "cancellation_time": iso(t_end) if mode != "boarded" else None,
            "cancellation_fee": fee_amt if (mode != "boarded" and fee_applied) else 0.0,
            "cancellation_reason": cancel_reason_out,
            # Added by us:
            "trip_type": trip_type, "booked_at": iso(t_booked),
            "matched_at": iso(matched_at), "eta_at_assignment_min": eta, "cancelled_by": cancelled_by,
            "trip_completed": mode == "boarded", "waiting_fee": wait_fee,
            "payment_status": "declined" if (payment == "declined" and fee_applied) else "captured"
            if (fee_applied or wait_fee) else "n/a",
        },
        "cancellation_policy": pol,
        "gps_telemetry": gps,
        "rider_app_location": rloc if rloc is not None else
            {"available": False, "note": "Rider app location not shared during this trip."},
        "chat_logs": chats,
        "app_events": ev,
        "policy_ref": POLICY_VERSION,
    }

    # metrics for the answer key (never shipped inside the case)
    valid = [g for g in gps if g["speed_kmh"] <= NS_POL["stationary_max_kmh"] and
             hav(pin, (g["lat"], g["lng"])) * 1000 <= NS_POL["arrival_radius_m"]
             and T(g["timestamp"][:19]) <= t_wait_end]
    if tapped:
        valid = [g for g in valid if T(g["timestamp"][:19]) >= t_event]
    t_valid = T(valid[0]["timestamp"][:19]) if valid else None
    contacts = [c for c in chats if c["sender"] == "driver"]
    metrics = {
        "profile": profile, "mode": mode, "trip_type": trip_type,
        "driver_stop_dist_m": round(hav(pin, stop_pt) * 1000),
        "tap_dist_m": d_event_m,
        "system_wait_min": round(tap_wait, 2) if tapped else None,
        "valid_arrival": iso(t_valid) if t_valid else None,
        "valid_wait_min": round((t_wait_end - t_valid).total_seconds() / 60, 2) if t_valid else None,
        "late_vs_eta_min": round((t_valid - t_sched).total_seconds() / 60, 2) if t_valid else None,
        "since_match_min": round((t_end - matched_at).total_seconds() / 60, 2),
        "driver_messages_and_calls": len(contacts),
        "fee_applied": bool(fee_applied), "waiting_fee": wait_fee,
    }
    return case, metrics


def _pos_at(gps, t, default):
    best, bd = default, None
    for g in gps:
        d = abs((T(g["timestamp"][:19]) - t).total_seconds())
        if bd is None or d < bd:
            best, bd = (g["lat"], g["lng"]), d
    return best


# --------------------------------------------------------------------------
# Route deviation cases
# --------------------------------------------------------------------------

def build_rd(cid, *, title, pickup, dropoff, t0, rider, driver, desc, planned, actual,
             speed, planned_speed, surge=1.0, erp_planned=(), erp_actual=(), promo=None,
             chat=(), extra_events=(), incidents=None, meter_km=None, gap=None,
             filed_after_min=None, wait_pick=7, charged_surge=None, meter_factor=None,
             filed_by="rider", dest_edit=None, orig_dropoff=None):
    """
    planned / actual: lists of waypoints between pickup and dropoff.
        In `actual`, an item {"stop": minutes, "label": str} means the car is stationary
        at the previous point for that long.
    erp_planned / erp_actual: lists of (gantry name, charge)
    promo: {"code", "amount", "applied": bool}
    dest_edit: None, "accepted" (rider edited the destination, driver accepted, fee charged) or
               "unrequested" (the same fee is on the receipt but no edit request exists)
    chat / extra_events: (minutes after trip start, ...)
    gap: (start, end) minutes after trip start with no GPS pings
    """
    rng = rng_for(cid)
    t0 = T(t0)
    a, b = ppos(pickup), ppos(dropoff)
    t_start = t0 + _m(wait_pick)

    if not planned:  # the app's road route (about 1.28 x the straight line), see lib.road_via
        planned = [road_via(pickup, dropoff)]
    planned_pts = [a] + list(planned) + [b]
    planned_km = poly_km(planned_pts)
    planned_min = planned_km / planned_speed * 60

    flat = []
    for x in actual:
        flat.extend(x) if isinstance(x, Path) else flat.append(x)
    actual = flat
    # The driven path. OnLine points sit on the planned route: the car follows the planned route to
    # reach them. An empty list means the car drove the planned route exactly.
    if not actual:
        actual = list(planned)
    elif any(isinstance(x, OnLine) for x in actual):
        expanded, via_done = [], False
        for x in actual:
            if isinstance(x, OnLine) and not via_done and x.f > 0.5:
                expanded += list(planned)
                via_done = True
            expanded.append(x)
        if not via_done:
            expanded += list(planned)
        actual = expanded

    # actual timeline segments
    segs, prev = [], a
    for item in list(actual) + [b]:
        if isinstance(item, dict):
            segs.append(("stop", prev, item["stop"], item))
        else:
            km = hav(prev, item)
            segs.append(("move", prev, item, km / speed * 60))
            prev = item
    actual_pts = [a] + [x for x in actual if not isinstance(x, dict)] + [b]
    actual_km = poly_km(actual_pts)
    stop_min = sum(s[2] for s in segs if s[0] == "stop")
    total_min = sum(s[3] for s in segs if s[0] == "move") + stop_min

    def pos_at(minute):
        acc = 0.0
        for s in segs:
            dur = s[3] if s[0] == "move" else s[2]
            if minute <= acc + dur:
                if s[0] == "stop":
                    return s[1], 0
                f = (minute - acc) / dur if dur else 1
                return lerp(s[1], s[2], f), speed
            acc += dur
        return b, 0

    gps, m = [], 0.0
    while m < total_min:
        p, spd = pos_at(m)
        if spd:
            spd = round(spd * rng.uniform(0.75, 1.2))
            p = move(p, rng.uniform(0, 8), rng.uniform(0, 360))
        else:
            p = move(p, rng.uniform(0.5, 3), rng.uniform(0, 360))  # a stopped car's GPS still jitters
        gps.append({"timestamp": iso(t_start + _m(m)), **latlng(p), "speed_kmh": spd,
                    "accuracy_m": round(rng.uniform(4, 10), 1), "status": "on_trip"})
        m += 1.0
    gps.append({"timestamp": iso(t_start + _m(total_min)), **latlng(b), "speed_kmh": 0,
                "accuracy_m": round(rng.uniform(4, 10), 1), "status": "completed"})
    if gap:
        g0, g1 = t_start + _m(gap[0]), t_start + _m(gap[1])
        gps = [g for g in gps if not (g0 <= T(g["timestamp"][:19]) <= g1)]

    erp_p = money(sum(c for _, c in erp_planned))
    erp_a = money(sum(c for _, c in erp_actual))
    promo_amt = promo["amount"] if promo else 0.0
    est = fare(planned_km, planned_min, surge, erp_p, promo_amt)
    m_km = actual_km * meter_factor if meter_factor else (meter_km if meter_km is not None else actual_km)
    charged = fare(m_km, total_min, charged_surge or surge, erp_a,
                   promo_amt if (promo and promo["applied"]) else 0.0)
    charged["promo_code"] = promo["code"] if (promo and promo["applied"]) else None
    if dest_edit:
        charged["destination_change_fee"] = RD_POL["dest_change_fee"]
        charged["total"] = money(charged["total"] + RD_POL["dest_change_fee"])
    charged["erp_gantries_passed"] = [{"gantry": n, "charge": c} for n, c in erp_actual]

    ev = []

    def add(t, typ, details):
        ev.append({"timestamp": iso(t), "event_type": typ, "details": details})

    trip_id = "TRIP-" + cid
    promo_txt = ""
    if promo:
        promo_txt = f" Promo code {promo['code']} validated (-${promo['amount']:.2f})."
    if dest_edit == "accepted" and orig_dropoff:
        add(t0, "booking_confirmed",
            f"Rider {rider['rider_id']} booked trip {trip_id} from {place(pickup)['name']} to "
            f"{place(orig_dropoff)['name']}. Surge x{surge}.{promo_txt}")
    else:
        add(t0, "booking_confirmed",
            f"Rider {rider['rider_id']} booked trip {trip_id} from {place(pickup)['name']} to "
            f"{place(dropoff)['name']}. Upfront estimate ${est['total']:.2f} for planned route "
            f"{planned_km:.1f} km / {planned_min:.0f} min. Surge x{surge}.{promo_txt}")
    add(t0 + timedelta(seconds=15), "driver_assigned",
        f"Driver {driver['driver_id']} ({driver['name']}, {driver['vehicle']}) assigned.")
    add(t_start - timedelta(seconds=60), "driver_arrived", "Driver GPS within 8 m of pickup point.")
    add(t_start, "trip_started", "Rider boarded. Trip meter started.")
    if dest_edit == "accepted":
        frm = f" from {place(orig_dropoff)['name']}" if orig_dropoff else ""
        add(t_start + _m(2.0), "destination_edit_requested",
            f"Rider requested to change the destination{frm} to {place(dropoff)['name']}.")
        add(t_start + _m(2.5), "destination_edit_accepted",
            f"Driver accepted the destination change. Route and upfront estimate re-quoted for the new "
            f"destination: ${est['total']:.2f} for {planned_km:.1f} km / {planned_min:.0f} min. A "
            f"${RD_POL['dest_change_fee']:.2f} add/edit destination fee will apply.")
    for (mins, typ, details) in extra_events:
        add(t_start + _m(mins), typ, details)
    acc = 0.0
    for s in segs:
        if s[0] == "move":
            acc += s[3]
            continue
        info = s[3]
        if info.get("event_start"):
            add(t_start + _m(acc), info["event_start"][0], info["event_start"][1])
        acc += s[2]
        if info.get("event_end"):
            add(t_start + _m(acc), info["event_end"][0], info["event_end"][1])
    t_end = t_start + _m(total_min)
    add(t_end, "trip_completed",
        f"Trip completed at {place(dropoff)['name']}. Meter distance {m_km:.2f} km, duration {total_min:.1f} min.")
    add(t_end + timedelta(seconds=20), "payment_captured",
        f"${charged['total']:.2f} charged to rider payment method ({rider['payment_method']}).")
    ev.sort(key=lambda e: e["timestamp"])

    chats = []
    for c in chat:
        mins, sender, typ, content = c[:4]
        chats.append({"timestamp": iso(t_start + _m(mins)), "sender": sender, "type": typ,
                      "content": content})
    chats.sort(key=lambda c: c["timestamp"])

    case = {
        "dispute_ticket": {
            "dispute_id": cid, "trip_id": trip_id, "filed_by": filed_by,
            "dispute_type": "route_deviation", "description": desc,
            "filed_at": iso(t_end + _m(filed_after_min if filed_after_min is not None
                                       else rng.randint(40, 26 * 60))), "status": "open",
        },
        "rider_profile": rider,
        "driver_profile": driver,
        "trip_data": {
            "trip_id": trip_id, "rider_id": rider["rider_id"], "driver_id": driver["driver_id"],
            "pickup_location": place(pickup), "dropoff_location": place(dropoff),
            "booked_at": iso(t0), "trip_start": iso(t_start), "trip_end": iso(t_end),
            "planned_route": {
                "distance_km": round(planned_km, 2),
                "duration_min": round(planned_min, 1),
                "waypoints": [latlng(p, 5) for p in planned_pts],
                "erp_gantries": [{"gantry": n, "charge": c} for n, c in erp_planned],
            },
            "upfront_estimate": est,
        },
        "fare_breakdown": charged,
        "gps_telemetry": gps,
        "chat_logs": chats,
        "app_events": ev,
        "traffic_incidents": {
            "source": "LTA traffic incident feed (mock)",
            "query_window": [iso(t_start), iso(t_end)],
            "incidents": [
                {k: v for k, v in inc.items() if k not in ("start_offset", "end_offset")}
                | {"reported_at": iso(t_start + _m(inc["start_offset"])),
                   "cleared_at": iso(t_start + _m(inc["end_offset"]))}
                for inc in (incidents or [])
            ],
        },
        "policy_ref": POLICY_VERSION,
    }
    dev_km = actual_km - planned_km
    metrics = {
        "planned_km": round(planned_km, 2), "planned_min": round(planned_min, 1),
        "actual_km": round(actual_km, 2), "meter_km": round(m_km, 2),
        "actual_min": round(total_min, 1), "stop_min": stop_min,
        "dev_km": round(dev_km, 2), "dev_pct": round(dev_km / planned_km * 100, 1),
        "estimate": est["total"], "charged": charged["total"], "surge": surge,
        "erp_planned": erp_p, "erp_actual": erp_a,
    }
    return case, metrics
