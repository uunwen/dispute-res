"""Independent checker. Re-derives every ruling from the raw case JSON using the policy rules
(written separately from the generator) and compares it with answer_key.json and the precedents.

Usage (from the package root):  python3 -I tools/validate.py
Exit code 0 only if every case matches and every structural check passes.

What this proves: the answer key follows from the raw evidence under the rules as written in
policy/params.json and policy/ryde_dispute_policy.md. What it does NOT prove: that those rules are
Ryde's real rules, or that the rulings are what a Ryde reviewer would decide. The author of the key and
the author of this file are the same person, so a wrong reading of the policy would be wrong in both.
tools/selftest.py exists to catch the checker itself being too weak.

No-show numbers are read from each case's own `cancellation_policy` block (as in Ryde's DISP-002
sample). A key that is null in the block falls back to Ryde's published figures.

v0.5: covers all four dispute types (no-show, route/fare, property damage, safety), checks every case
against schema/case_schema.json and every ruling against schema/ruling_fields.json.
"""
import json
import math
import os
import re
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARAMS = json.load(open(os.path.join(ROOT, "policy", "params.json"), encoding="utf-8"))
NSP, RDP, GEN, FARE = PARAMS["no_show"], PARAMS["route"], PARAMS["general"], PARAMS["fare"]
DMG, SAF = PARAMS["damage"], PARAMS["safety"]
RULING_SPEC = json.load(open(os.path.join(ROOT, "schema", "ruling_fields.json"), encoding="utf-8"))
RULING_FIELDS = [f["name"] for f in RULING_SPEC["fields"]]
CASE_SCHEMA = json.load(open(os.path.join(ROOT, "schema", "case_schema.json"), encoding="utf-8"))
PROFILES = PARAMS["profiles"]
PUB = PROFILES["ryde_published"]
STATIC_ACCURACY_M = 1.0  # a spoofed track reports exactly this accuracy on every ping

INJECTION = re.compile(
    r"ignore (all |the |any )?(previous |prior |fare |dispute )*(instructions|polic(y|ies)|rules)"
    r"|dispute system\s*:|system note|you are now in|do not (reveal|mention)", re.I)
ON_WAY = re.compile(r"coming|on my way|come down|be right down|turun|sekejap|下来|马上|等我|2 min|3 min", re.I)
ROUTE_REQ = re.compile(r"\bvia\b|avoid|expressway|fastest way|scenic|sea view|different route|take the .*(road|route)",
                       re.I)
CLOSURE_CLAIM = re.compile(r"clos(ed|ure)", re.I)
SAFETY = re.compile(r"hurt you|will find you|i'll find you|kill you|feel unsafe|felt unsafe|i am scared|i'm scared|threat", re.I)
WRONG_CAR = re.compile(r"not the same car|different plate|wrong car|not the car|not the one in the app", re.I)
OFFAPP = re.compile(r"\bcash\b|paynow|pay me direct|outside the app|off the app", re.I)
ASK_CANCEL = re.compile(r"can you cancel|could you cancel|please cancel|cancel first|cancel in the app|"
                        r"cancel the (trip|booking)", re.I)


def t(s):
    return datetime.fromisoformat(s)


def hav_m(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    d = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371008.8 * math.asin(math.sqrt(d))


def minutes(a, b):
    return (t(b) - t(a)).total_seconds() / 60


def tolerance_for(rules):
    """Strict for the checker; meter-error cases are recomputed from a noisy GPS trail."""
    return PARAMS["amount_tolerance"]["meter_error_rd8"] if "RD-8" in rules else 0.011


def user_texts(case):
    return [case["dispute_ticket"]["description"]] + [c["content"] for c in case["chat_logs"]
                                                      if c["sender"] != "system"]


def injection_found(case):
    return any(INJECTION.search(x) for x in user_texts(case))


def safety_found(case):
    return any(SAFETY.search(x) for x in user_texts(case))


def gps_issues(gps, start, end):
    """Set of {'spoof','gap'} found in the pings between start and end (ISO strings)."""
    pts = sorted([g for g in gps if start <= g["timestamp"] <= end], key=lambda g: g["timestamp"])
    out, gap_pair = set(), None
    marks = [{"timestamp": start, "lat": None}] + pts + [{"timestamp": end, "lat": None}]
    for a, b in zip(marks, marks[1:]):
        if minutes(a["timestamp"], b["timestamp"]) > GEN["gps_gap_min"]:
            out.add("gap")
            gap_pair = (a, b)
    # speed between consecutive pings, looking a little before the window as well
    wide = sorted([g for g in gps if minutes(start, g["timestamp"]) >= -5 and g["timestamp"] <= end],
                  key=lambda g: g["timestamp"])
    for a, b in zip(wide, wide[1:]):
        dt = minutes(a["timestamp"], b["timestamp"])
        if dt > 0:
            kmh = hav_m((a["lat"], a["lng"]), (b["lat"], b["lng"])) / 1000 / (dt / 60)
            if kmh > GEN["gps_impossible_kmh"]:
                out.add("spoof")
    stationary = [g for g in pts if g["speed_kmh"] == 0]
    if len(stationary) >= 3 and all(g.get("accuracy_m") == STATIC_ACCURACY_M for g in stationary):
        out.add("spoof")
    return out, gap_pair


# ---------------------------------------------------------------------------------------------
# No-show, cancellation and waiting fees
# ---------------------------------------------------------------------------------------------

def _blank(case):
    return dict(outcome=None, refund_amount=0.0, payer=None, driver_warning=False, escalate=False,
                security_flag=injection_found(case), driver_goodwill_paid_by_ryde=0.0,
                fraud_flag=False, provisional_outcome=None, rider_charge_amount=0.0, rider_warning=False,
                safety_referral=False)


def _escalate(r, prov, referral=False):
    r.update(outcome="escalate_to_human", escalate=True, provisional_outcome=prov, refund_amount=0.0,
             payer=None, driver_warning=False, driver_goodwill_paid_by_ryde=0.0, rider_charge_amount=0.0,
             rider_warning=False, safety_referral=referral)
    return r


def ns_core(case):
    """The ruling before the safety rule (G-4) is applied."""
    td, chat, gps, ev = case["trip_data"], case["chat_logs"], case["gps_telemetry"], case["app_events"]
    blk = {k: v for k, v in case["cancellation_policy"].items() if v is not None}  # null = not set (Part B)
    pol = {**PUB, **blk}
    thr, free = pol["no_show_threshold_min"], pol["free_wait_time_min"]
    block_fee = pol["cancellation_fee_after_wait"]
    comp = blk.get("driver_compensation", block_fee)
    extended = thr + NSP["rider_on_way_extra_min"]
    pin = (td["pickup_location"]["lat"], td["pickup_location"]["lng"])
    filed_by = case["dispute_ticket"]["filed_by"]
    rp, dp = case["rider_profile"], case["driver_profile"]
    r = _blank(case)

    mode = ("boarded" if td["trip_completed"] else "rider_cancel" if td["cancelled_by"] == "rider"
            else "driver_cancel")
    matched = td["matched_at"]
    sched = td["scheduled_time"]
    arrival = next((e for e in ev if e["event_type"] == "driver_arrived"), None)
    tap = arrival["timestamp"] if arrival else None
    if mode == "boarded":
        end = next(e["timestamp"] for e in ev if e["event_type"] == "trip_started")
        trip_end = next(e["timestamp"] for e in ev if e["event_type"] == "trip_completed")
    else:
        end = trip_end = td["cancellation_time"]
    start = tap or matched

    drv_chat = [c for c in chat if c["sender"] == "driver"]
    rid_chat = [c for c in chat if c["sender"] == "rider" and c["type"] == "message"]

    # a rider cancelled because the car did not match: nothing in the policy covers it (NS-15)
    if mode == "rider_cancel" and any(WRONG_CAR.search(c["content"]) for c in rid_chat):
        return _escalate(r, "full_refund", referral=True)

    # time bar (G-8): only for rider-filed requests
    if filed_by == "rider" and minutes(trip_end, case["dispute_ticket"]["filed_at"]) > \
            NSP["waiver_window_days"] * 24 * 60:
        r.update(outcome="no_action")
        return r

    issues, gap_pair = gps_issues(gps, start, end)
    if issues:
        if "spoof" in issues:
            r["fraud_flag"] = True  # G-10(f)
        prov = "full_refund"
        if issues == {"gap"} and gap_pair:  # G-11: both sides of the gap agree the driver was at the pin
            a, b = gap_pair
            if a["lat"] is not None and b["lat"] is not None and \
                    hav_m(pin, (a["lat"], a["lng"])) <= NSP["arrival_radius_m"] and \
                    hav_m(pin, (b["lat"], b["lng"])) <= NSP["arrival_radius_m"]:
                prov = "charge_upheld"
        return _escalate(r, prov)
    m = re.search(r"within (\d+) m", arrival["details"]) if arrival else None
    if arrival and m and int(m.group(1)) <= NSP["arrival_radius_m"]:
        near = [g for g in gps if tap <= g["timestamp"] <= end
                and hav_m(pin, (g["lat"], g["lng"])) <= NSP["arrival_contradiction_m"]]
        if not near:  # the app event and the raw GPS disagree and nothing else settles it
            return _escalate(r, "full_refund")

    valid = [g for g in gps if start <= g["timestamp"] <= end and g["speed_kmh"] <= NSP["stationary_max_kmh"]
             and hav_m(pin, (g["lat"], g["lng"])) <= NSP["arrival_radius_m"]]
    v_arr = min((g["timestamp"] for g in valid), default=None)
    wait = minutes(v_arr, end) if v_arr else None
    sys_wait = minutes(tap, end) if tap else None
    late = minutes(sched, v_arr) if v_arr else None
    tap_dist = None
    if tap:
        nearest = min(gps, key=lambda g: abs((t(g["timestamp"]) - t(tap)).total_seconds()))
        tap_dist = hav_m(pin, (nearest["lat"], nearest["lng"]))
    contacts = [c for c in drv_chat if tap and tap <= c["timestamp"] <= end]
    on_way = any(ON_WAY.search(c["content"]) and (v_arr or start) <= c["timestamp"] <= end for c in rid_chat)
    offapp = any(OFFAPP.search(c["content"]) for c in drv_chat)
    rl = case["rider_app_location"]
    rider_d = None
    if rl and rl["available"] and rl["pings"]:
        ds = [hav_m(pin, (p["lat"], p["lng"])) for p in rl["pings"] if start <= p["timestamp"] <= end]
        rider_d = min(ds) if ds else None

    def fraud_driver_far():  # G-10(a)
        return (tap_dist is not None and tap_dist > NSP["invalid_tap_far_m"]
                and (dp["warnings_last_30_days"] >= NSP["fraud_driver_warnings"] or dp["fraud_flags"] >= 1))

    def finish(outcome, amount=0.0, payer=None, warn=False, goodwill=0.0):
        r.update(outcome=outcome, refund_amount=round(amount, 2), payer=payer, driver_warning=warn,
                 driver_goodwill_paid_by_ryde=goodwill)
        if fraud_driver_far() or (offapp and mode != "boarded"):
            r["fraud_flag"] = True
        if outcome == "charge_upheld" and mode == "driver_cancel":
            if rp["account_age_days"] <= NSP["new_account_days"] and rp["total_trips"] == 0 \
                    and rp["fraud_flags"] >= 1:
                r["fraud_flag"] = True  # G-10(d)
        if outcome == "charge_upheld" and rider_d is not None and rider_d > NSP["invalid_tap_far_m"] \
                and rp["dispute_history"]["rejected"] >= NSP["fraud_rider_rejected"] and filed_by == "rider":
            r["fraud_flag"] = True  # G-10(c)
        return r

    def overcharge(fee_charged, fee_block):
        return fee_charged - fee_block > 0.005

    def noshow_validity():
        """(valid, payer, warn) for a driver's no-show cancellation or a waiting fee. NS-1 to NS-7, NS-10."""
        if v_arr is not None and late > NSP["late_driver_min"]:
            return False, "ryde", False
        if offapp:
            return False, "driver", True
        if v_arr is None:
            return False, "driver", True
        if mode == "driver_cancel" and not contacts:
            return False, "driver", True
        if wait > thr + (NSP["rider_on_way_extra_min"] if on_way else 0):
            return True, None, False
        # a cancelled trip: the driver left too early (driver's cost). A boarded trip: the app or the rider
        # caused the short wait, so the waiting fee is Ryde's cost and the driver is not warned.
        soft = ("driver", True) if mode == "driver_cancel" else ("ryde", False)
        if on_way and wait > thr:
            return (False,) + soft
        if sys_wait <= thr:
            return (False,) + soft
        if tap_dist is not None and tap_dist <= NSP["tap_good_faith_m"]:
            return False, "ryde", False
        return False, "driver", True

    # ---------------- driver cancelled as a no-show ----------------
    if mode == "driver_cancel":
        fee = td["cancellation_fee"]
        ok, payer, warn = noshow_validity()
        if filed_by == "driver":
            if ok:
                multi = td["pickup_location"].get("multi_entrance_venue") and rider_d is not None \
                    and NSP["entrance_mismatch_min_m"] <= rider_d <= NSP["entrance_mismatch_max_m"]
                if multi:
                    return finish("no_action", goodwill=comp)
                gw = comp if td.get("payment_status") == "declined" else 0.0
                finish("charge_upheld", goodwill=gw)
                r["rider_charge_amount"] = block_fee  # NS-12: the fee is applied now (G-6, v0.5 field)
                return r
            drv_fault = v_arr is None or (tap_dist is not None and tap_dist > NSP["tap_good_faith_m"]
                                          and wait is not None and wait <= thr)
            return finish("no_action", warn=bool(drv_fault))
        if fee <= 0:
            return finish("no_action")
        if ok:
            multi = td["pickup_location"].get("multi_entrance_venue") and rider_d is not None \
                and NSP["entrance_mismatch_min_m"] <= rider_d <= NSP["entrance_mismatch_max_m"]
            if multi:
                return finish("full_refund", fee, "ryde", False, goodwill=comp)
            if overcharge(fee, block_fee):
                return finish("partial_refund", fee - block_fee, "ryde", False)
            return finish("charge_upheld")
        return finish("full_refund", fee, payer, warn)

    # ---------------- rider cancelled in the app ----------------
    if mode == "rider_cancel":
        since_match = minutes(matched, end)
        adv = td["trip_type"] == "advance"
        if adv:
            in_window = (minutes(end, sched) >= pol["advance_free_before_min"]) or since_match <= free
        else:
            in_window = since_match <= free
        asked = any(ASK_CANCEL.search(c["content"]) for c in drv_chat)
        reached = any(g["timestamp"] <= end and g["speed_kmh"] <= NSP["stationary_max_kmh"]
                      and hav_m(pin, (g["lat"], g["lng"])) <= NSP["arrival_radius_m"] for g in gps)
        waived_late = (not reached) and minutes(sched, end) > NSP["late_driver_min"]
        # stalled: the last pings before the cancel are stationary and far from the pin for a while
        before = sorted([g for g in gps if g["timestamp"] <= end], key=lambda g: g["timestamp"])
        run = []
        for g in reversed(before):
            if g["speed_kmh"] <= NSP["stationary_max_kmh"] and hav_m(pin, (g["lat"], g["lng"])) > NSP["stalled_dist_m"]:
                run.append(g)
            else:
                break
        stalled = bool(run) and minutes(run[-1]["timestamp"], end) >= NSP["stalled_min"] \
            and minutes(run[0]["timestamp"], end) <= GEN["gps_gap_min"]
        if filed_by == "driver":
            if td["cancellation_fee"] > 0:
                return finish("no_action")
            if in_window or asked or waived_late or stalled:
                return finish("no_action")
            finish("charge_upheld")
            r["rider_charge_amount"] = block_fee  # NS-12
            return r
        if td["cancellation_fee"] <= 0:
            return finish("no_action")
        fee = td["cancellation_fee"]
        if in_window:
            return finish("full_refund", fee, "ryde", False)
        if asked:
            return finish("full_refund", fee, "driver", True)
        if waived_late or stalled:
            return finish("full_refund", fee, "ryde", False)
        if overcharge(fee, block_fee):
            return finish("partial_refund", fee - block_fee, "ryde", False)
        return finish("charge_upheld")

    # ---------------- waiting fee (rider boarded) ----------------
    fee = td["waiting_fee"]
    if fee <= 0:
        return finish("no_action")
    ok, payer, warn = noshow_validity()
    if ok:
        if overcharge(fee, pol["waiting_fee"]):
            return finish("partial_refund", fee - pol["waiting_fee"], "ryde", False)
        return finish("charge_upheld")
    return finish("full_refund", fee, payer, warn)


def derive_ns(case):
    core = ns_core(case)
    if core["escalate"] or not safety_found(case):
        return core
    out = dict(core)
    out.update(outcome="escalate_to_human", escalate=True, provisional_outcome=core["outcome"],
               refund_amount=0.0, payer=None, driver_warning=False, driver_goodwill_paid_by_ryde=0.0,
               rider_charge_amount=0.0, rider_warning=False, safety_referral=True)
    return out


# ---------------------------------------------------------------------------------------------
# Route deviation and fare disputes
# ---------------------------------------------------------------------------------------------

INCIDENT_NEAR_ROUTE_M = 300


def incident_on_route(inc, waypoints, trip_start, trip_end):
    """RD-4c: the feed confirms an incident on the planned route while the trip was running."""
    loc = inc.get("location")
    if not loc or inc["reported_at"] > trip_end or inc["cleared_at"] < trip_start:
        return False
    p = (loc["lat"], loc["lng"])
    pts = [(w["lat"], w["lng"]) for w in waypoints]
    for a, b in zip(pts, pts[1:]):
        n = max(1, int(hav_m(a, b) / 50))
        for i in range(n + 1):
            q = (a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n)
            if hav_m(p, q) <= INCIDENT_NEAR_ROUTE_M:
                return True
    return False


def rd_core(case):
    td, fb, gps = case["trip_data"], case["fare_breakdown"], case["gps_telemetry"]
    ev, chat = case["app_events"], case["chat_logs"]
    est, charged = td["upfront_estimate"], fb["total"]
    r = _blank(case)
    dp = case["driver_profile"]

    def partial(amount, payer, warn, fraud=False):
        r.update(outcome="partial_refund", refund_amount=round(amount + 1e-9, 2), payer=payer,
                 driver_warning=warn, fraud_flag=fraud)
        return r

    if fb["surge_multiplier"] - est["surge_multiplier"] > 1e-9:  # RD-13
        pre = fb["base_fare"] + fb["distance_charge"] + fb["time_charge"]
        return partial(pre * (fb["surge_multiplier"] - est["surge_multiplier"]), "ryde", False)
    dest_fee = fb.get("destination_change_fee", 0.0)
    if dest_fee > 0 and not any(e["event_type"] == "destination_edit_accepted" for e in ev):  # RD-11
        return partial(dest_fee, "ryde", False)
    if est["promo_discount"] > 0 and not fb.get("promo_code"):
        return partial(est["promo_discount"], "ryde", False)

    pts = sorted(gps, key=lambda g: g["timestamp"])
    gps_km = sum(hav_m((a["lat"], a["lng"]), (b["lat"], b["lng"])) for a, b in zip(pts, pts[1:])) / 1000
    has_gap = any(minutes(a["timestamp"], b["timestamp"]) > GEN["gps_gap_min"] for a, b in zip(pts, pts[1:]))
    meter_km = fb["distance_km"]
    if not has_gap and abs(meter_km - gps_km) / gps_km > RDP["meter_mismatch"]:
        right = (FARE["base"] + FARE["per_km"] * gps_km + FARE["per_min"] * fb["duration_min"]) \
            * fb["surge_multiplier"] + fb["erp_charges"] + FARE["platform_fee"] - fb["promo_discount"]
        return partial(charged - right, "ryde", False)

    starts = [e for e in ev if e["event_type"] == "unscheduled_stop_start"]
    ends = [e for e in ev if e["event_type"] == "unscheduled_stop_end"]
    rider_added = any(e["event_type"] == "stop_added" for e in ev)
    if starts and ends and not rider_added:
        stop_min = minutes(starts[0]["timestamp"], ends[0]["timestamp"])
        if stop_min > RDP["stop_free_min"]:
            return partial(stop_min * FARE["per_min"] * fb["surge_multiplier"], "driver", True)

    planned_km = td["planned_route"]["distance_km"]
    dev = (meter_km - planned_km) / planned_km
    tol = max(RDP["tol_pct"], RDP["tol_km"] / planned_km)
    if dev <= tol:
        r.update(outcome="no_action")
        return r
    if has_gap:
        return _escalate(r, "partial_refund")

    if any(c["sender"] == "rider" and ROUTE_REQ.search(c["content"]) for c in chat) or rider_added:
        r.update(outcome="no_action")
        return r
    if any(e["event_type"] == "navigation_reroute" for e in ev):
        cap = (1 + RDP["app_reroute_cap"]) * est["total"]
        if charged > cap:
            return partial(charged - cap, "ryde", False)
        r.update(outcome="no_action")
        return r
    if any(incident_on_route(i, td["planned_route"]["waypoints"], td["trip_start"], td["trip_end"])
           for i in case["traffic_incidents"]["incidents"]):
        r.update(outcome="no_action")
        return r
    erp_p = sum(g["charge"] for g in td["planned_route"]["erp_gantries"])
    erp_a = sum(g["charge"] for g in fb["erp_gantries_passed"])
    if erp_p > erp_a:
        if charged <= est["total"]:
            r.update(outcome="no_action")
            return r
        return partial(charged - est["total"], "ryde", False)

    claimed_closure = any(c["sender"] == "driver" and CLOSURE_CLAIM.search(c["content"]) for c in chat)
    pattern = dp["warnings_last_30_days"] >= 1 or dp["fraud_flags"] >= 1
    warn = (not claimed_closure) or pattern
    fraud = dp["warnings_last_30_days"] >= RDP["fraud_driver_warnings"]  # G-10(e)
    return partial(charged - est["total"], "driver", warn, fraud)


def derive_rd(case):
    core = rd_core(case)
    if core["escalate"] or not safety_found(case):
        return core
    out = dict(core)
    out.update(outcome="escalate_to_human", escalate=True, provisional_outcome=core["outcome"],
               refund_amount=0.0, payer=None, driver_warning=False, driver_goodwill_paid_by_ryde=0.0,
               fraud_flag=False, rider_charge_amount=0.0, rider_warning=False, safety_referral=True)
    return out


# ---------------------------------------------------------------------------------------------
# Property damage and cleaning fees (Part PD, v0.5)
# ---------------------------------------------------------------------------------------------

def _plate(vehicle):
    m = re.search(r"\(([^)]+)\)", vehicle)
    return m.group(1) if m else None


def _h(a, b):
    return (t(b) - t(a)).total_seconds() / 3600


def derive_pd(case):
    td, att, ev = case["trip_data"], case["attachments"], case["app_events"]
    claim = td["damage_claim"]
    plate = _plate(case["driver_profile"]["vehicle"])
    start, end = td["trip_start"], td["trip_end"]
    nxt = next((e["timestamp"] for e in ev if e["event_type"] == "driver_next_trip_started"), None)
    r = _blank(case)
    driver_filed = case["dispute_ticket"]["filed_by"] == "driver"
    charged = claim["amount_charged"]
    photos = [a for a in att if a["attachment_type"] == "photo"]
    receipts = [a for a in att if a["attachment_type"] == "receipt"]

    def false_ev(a):  # PD-7
        v = a["simulated_vision_analysis"]
        return (a["captured_at"] < start or v["duplicate_of"] is not None
                or (v["plate_read"] is not None and v["plate_read"] != plate)
                or v["ai_generated_likelihood"] >= DMG["ai_generated_threshold"])

    def valid(a):  # PD-6
        return (start <= a["captured_at"] and _h(end, a["captured_at"]) <= DMG["photo_window_after_trip_h"]
                and (nxt is None or a["captured_at"] < nxt) and not false_ev(a))

    caps = DMG["caps"]
    good = [a for a in photos if valid(a)]
    shown = [a["simulated_vision_analysis"]["mess_type"] for a in good
             if a["simulated_vision_analysis"]["mess_type"] != "none"]
    has_plate = any(a["simulated_vision_analysis"]["plate_read"] == plate for a in good)
    late = _h(end, claim["submitted_at"]) > DMG["claim_deadline_h"]
    trip_day = t(end).date()

    def receipt_ok(a):
        d = a["receipt_details"]
        days = (datetime.fromisoformat(d["cleaning_date"]).date() - trip_day).days
        return (d["professional_cleaning"] and all(d[k] for k in ("company_name", "uen", "address", "contact_number"))
                and d["car_plate"] == plate and d["signed"] and d["company_stamp"]
                and 0 <= days <= DMG["cleaning_within_days"])

    rec = next((a for a in receipts if receipt_ok(a)), None)

    if any(false_ev(a) for a in photos):  # PD-7, G-10(g)
        r.update(fraud_flag=True, driver_warning=True)
        if driver_filed:
            r["outcome"] = "no_action"
        else:
            r.update(outcome="full_refund", refund_amount=charged, payer="driver")
        return r
    if any(m in DMG["gap_types"] for m in shown):  # PD-9: repairs are a policy gap
        ok = (not late) and bool(shown) and has_plate
        prov = "charge_upheld" if ok else ("no_action" if driver_filed else "full_refund")
        return _escalate(r, prov)
    claimable = [m for m in shown if m not in DMG["not_claimable"] and m in caps]
    cap = max((caps[m] for m in claimable), default=0.0)
    approved = round(min(rec["receipt_details"]["amount"], cap), 2) if rec else 0.0
    ok = (not late) and bool(shown) and has_plate and rec is not None and approved > 0
    if driver_filed:
        if ok:
            r.update(outcome="charge_upheld", rider_charge_amount=approved)
        else:
            r["outcome"] = "no_action"
        return r
    if not ok:
        r.update(outcome="full_refund", refund_amount=charged, payer="driver")
        return r
    if charged <= approved + 0.005:
        r["outcome"] = "charge_upheld"
        return r
    over_claim = caps.get(claim["mess_type_claimed"], 0.0) > cap
    r.update(outcome="partial_refund", refund_amount=round(charged - approved, 2),
             payer="driver" if over_claim else "ryde")
    return r


# ---------------------------------------------------------------------------------------------
# Safety incidents (Part SF, v0.5)
# ---------------------------------------------------------------------------------------------

THREAT = re.compile(r"hurt you|kill you|i know where you live|will find you|beat (you|me)( up)?|you will regret|"
                    r"smash your|break your|pukul|打你|揍你", re.I)
PHYSICAL = re.compile(r"grabbed|touched (me|my)|hit me|pushed me|slapped|punched", re.I)
SEXUAL = re.compile(r"sexy|kiss me|send me (a |your )?(photo|pic)|your body|sleep with", re.I)
STOP_REQ = re.compile(r"stop the car|let me (get )?out|i want to get out", re.I)
STOP_REFUSED = re.compile(r"cannot stop|can't stop|won't stop|not stopping", re.I)
ABUSE = re.compile(r"\bidiot\b|\bstupid\b|\buseless\b|\bbodoh\b|笨蛋|闭嘴|shut up|go to hell|\bdamn you\b", re.I)
DISCRIM = re.compile(r"your people|your kind|your religion|your race|go back to your country|you foreigners", re.I)
SPEED_CLAIM = re.compile(r"speed|too fast|racing|reckless|dangerous", re.I)
CHAT_CLAIM = re.compile(r"\bchat\b|messag|texted", re.I)
EARLY_CLAIM = re.compile(r"dropped me|kicked me out|halfway|told me to get out|ended the trip|left me", re.I)


def derive_sf(case):
    r = _blank(case)
    ev, chat, gps, fb = case["app_events"], case["chat_logs"], case["gps_telemetry"], case["fare_breakdown"]
    desc = case["dispute_ticket"]["description"]
    filed_by = case["dispute_ticket"]["filed_by"]
    texts = user_texts(case)
    drv = [c["content"] for c in chat if c["sender"] == "driver"]
    rid = [c["content"] for c in chat if c["sender"] == "rider"]
    reporter = case["rider_profile"] if filed_by == "rider" else case["driver_profile"]
    fare_total = fb["total"]

    trigger = (any(THREAT.search(x) or PHYSICAL.search(x) or SEXUAL.search(x) for x in texts)
               or any(e["event_type"] == "sos_triggered" for e in ev)
               or (any(STOP_REQ.search(x) for x in rid) and any(STOP_REFUSED.search(x) for x in drv)))
    prov = "full_refund" if filed_by == "rider" else "charge_upheld"
    if trigger:  # SF-1
        return _escalate(r, prov, referral=True)

    over = [g["speed_kmh"] - g["speed_limit_kmh"] for g in sorted(gps, key=lambda g: g["timestamp"])
            if g["speed_limit_kmh"] is not None]
    run = best = 0
    for o in over:
        run = run + 1 if o > SAF["over_limit_consecutive_kmh"] else 0
        best = max(best, run)
    dangerous = best >= SAF["consecutive_pings"] or any(o > SAF["over_limit_single_kmh"] for o in over)
    driver_abuse = any(ABUSE.search(x) or DISCRIM.search(x) for x in drv)
    rider_abuse = any(ABUSE.search(x) or DISCRIM.search(x) for x in rid)
    early = next((e for e in ev if e["event_type"] == "trip_ended_early"), None)

    if dangerous or driver_abuse:  # SF-2, SF-3
        r.update(outcome="full_refund", refund_amount=fare_total, payer="driver", driver_warning=True,
                 safety_referral=True)
        return r
    if early:  # SF-4
        m = re.search(r"Reason selected: ([a-z_ ]+)\.", early["details"])
        reason = m.group(1) if m else "none given"
        if reason == "rider_abuse" and rider_abuse:
            r.update(outcome="charge_upheld", rider_warning=True, safety_referral=True)
            return r
        r.update(outcome="full_refund", refund_amount=fare_total, payer="driver", driver_warning=True,
                 safety_referral=True)
        return r
    if rider_abuse:  # SF-3 by the rider
        r.update(outcome="charge_upheld", rider_warning=True, safety_referral=True)
        return r
    if SPEED_CLAIM.search(desc) or CHAT_CLAIM.search(desc) or EARLY_CLAIM.search(desc):  # SF-6
        r["outcome"] = "no_action"
        if reporter["dispute_history"]["rejected"] >= SAF["reporter_fraud_rejected"]:
            r["fraud_flag"] = True  # G-10(h)
        return r
    return _escalate(r, prov, referral=True)  # SF-5: nothing on record can check it


def derive(case):
    kind = case["dispute_ticket"]["dispute_type"]
    return {"no_show_charge": derive_ns, "route_deviation": derive_rd, "property_damage": derive_pd,
            "safety_incident": derive_sf}[kind](case)


# ---------------------------------------------------------------------------------------------
# Loading, comparing, structure
# ---------------------------------------------------------------------------------------------

def load():
    key = json.load(open(os.path.join(ROOT, "test_set", "answer_key.json"), encoding="utf-8"))
    cases = {}
    for k in key:
        cases[k["id"]] = json.load(open(os.path.join(ROOT, "test_set", "cases", k["id"] + ".json"),
                                        encoding="utf-8"))
    precs = {}
    pdir = os.path.join(ROOT, "precedents", "cases")
    for fn in sorted(os.listdir(pdir)):
        d = json.load(open(os.path.join(pdir, fn), encoding="utf-8"))
        precs[fn[:-5]] = d
    return key, cases, precs


COMPARE_FIELDS = ("outcome", "payer", "driver_warning", "escalate", "security_flag",
                  "driver_goodwill_paid_by_ryde", "fraud_flag", "provisional_outcome", "rider_warning",
                  "safety_referral")


def compare(derived, exp, tol):
    bad = []
    for f in COMPARE_FIELDS:
        if derived[f] != exp[f]:
            bad.append(f"{f}: derived {derived[f]!r} vs key {exp[f]!r}")
    for f in ("refund_amount", "rider_charge_amount"):
        if abs(derived[f] - exp[f]) > tol:
            bad.append(f"{f}: derived {derived[f]} vs key {exp[f]}")
    return bad


def schema_errors(value, sch, path="case"):
    """Checks a value against the draft-07 subset used in schema/case_schema.json and ruling_schema.json."""
    if "anyOf" in sch:
        if any(not schema_errors(value, s, path) for s in sch["anyOf"]):
            return []
        return [f"{path}: matches none of the allowed shapes"]
    if "enum" in sch:
        return [] if value in sch["enum"] else [f"{path}: {value!r} not in {sch['enum']}"]
    typ = sch.get("type")
    types = typ if isinstance(typ, list) else [typ] if typ else []
    pyok = {"object": lambda v: isinstance(v, dict), "array": lambda v: isinstance(v, list),
            "string": lambda v: isinstance(v, str), "boolean": lambda v: isinstance(v, bool),
            "null": lambda v: v is None,
            "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
            "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool)}
    if types and not any(pyok[x](value) for x in types):
        return [f"{path}: expected {types}, got {type(value).__name__}"]
    errs = []
    if isinstance(value, dict) and "properties" in sch:
        req = sch.get("required", [])
        errs += [f"{path}: missing key {k}" for k in req if k not in value]
        if sch.get("additionalProperties") is False:
            errs += [f"{path}: unexpected key {k}" for k in value if k not in sch["properties"]]
        for k, v in value.items():
            if k in sch["properties"]:
                errs += schema_errors(v, sch["properties"][k], f"{path}.{k}")
    if isinstance(value, list) and "items" in sch:
        for i, v in enumerate(value):
            errs += schema_errors(v, sch["items"], f"{path}[{i}]")
    return errs


def leaf_paths(o, p=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from leaf_paths(v, p + k + ".")
    elif isinstance(o, list):
        for x in o:
            yield from leaf_paths(x, p + "[].")
    else:
        yield p[:-1]


def format_checks(case):
    """Every no-show case must carry the fields Ryde's DISP-002 sample has. Route cases only need the shared parts."""
    req = json.load(open(os.path.join(ROOT, "schema", "disp002_required_fields.json"),
                         encoding="utf-8"))["required_paths"]
    have = set(leaf_paths(case))
    cid = case["dispute_ticket"]["dispute_id"]
    if case["dispute_ticket"]["dispute_type"] != "no_show_charge":
        shared = ("dispute_ticket.", "rider_profile.", "driver_profile.", "gps_telemetry.", "chat_logs.",
                  "app_events.", "trip_data.trip_id", "trip_data.rider_id", "trip_data.driver_id",
                  "trip_data.pickup_location", "trip_data.dropoff_location")
        req = [p for p in req if p.startswith(shared)]

    def list_is_empty(path):
        """An empty list (for example no chat messages) has no items to carry the fields."""
        if ".[]." not in path:
            return False
        node = case
        for part in path.split(".[].")[0].split("."):
            node = node.get(part, {}) if isinstance(node, dict) else {}
        return isinstance(node, list) and not node

    # fields the DISP-002 sample has that are legitimately null in some of our cases
    nullable = ("trip_data.driver_arrival_time", "trip_data.driver_wait_start", "trip_data.cancellation_time",
                "trip_data.cancellation_reason")
    return [f"{cid}: missing DISP-002 field {p}" for p in req
            if p not in have and not list_is_empty(p) and p not in nullable]


def structure_checks(case):
    errs = format_checks(case)
    cid = case["dispute_ticket"]["dispute_id"]
    sch = [f"{cid}: {e}" for e in schema_errors(case, CASE_SCHEMA)]
    if sch:  # the checks below assume the shared shape
        return errs + sch
    for name in ("chat_logs", "app_events", "gps_telemetry"):
        ts = [x["timestamp"] for x in case[name]]
        if ts != sorted(ts):
            errs.append(f"{cid}: {name} not in time order")
    blk = case["cancellation_policy"]
    is_ns = case["dispute_ticket"]["dispute_type"] == "no_show_charge"
    if is_ns != (blk is not None):
        errs.append(f"{cid}: cancellation_policy must be present exactly for no-show cases")
    if blk is not None and {k: v for k, v in blk.items() if v is not None} not in PROFILES.values():
        errs.append(f"{cid}: cancellation_policy block is not one of the profiles in policy/params.json")
    for name, kinds in (("fare_breakdown", ("route_deviation", "property_damage", "safety_incident")),
                        ("traffic_incidents", ("route_deviation",)), ("rider_app_location", ("no_show_charge",))):
        if (case[name] is not None) != (case["dispute_ticket"]["dispute_type"] in kinds):
            errs.append(f"{cid}: {name} should be null exactly when the dispute type does not use it")
    if (case["trip_data"]["damage_claim"] is not None) != (case["dispute_ticket"]["dispute_type"] == "property_damage"):
        errs.append(f"{cid}: damage_claim should be set exactly for property damage cases")
    # answer words must not appear anywhere except inside user-written text (an injection may quote them)
    scrubbed = json.loads(json.dumps(case))
    scrubbed["dispute_ticket"]["description"] = ""
    for c in scrubbed["chat_logs"]:
        if c["sender"] != "system":
            c["content"] = ""
    blob = json.dumps(scrubbed)
    for leak in ("\"expected", "answer_key", "\"ruling\"", "full_refund", "charge_upheld", "partial_refund",
                 "escalate_to_human", "no_action", "\"why\"", "fraud_flag\":", "provisional"):
        if leak in blob:
            errs.append(f"{cid}: possible answer leak ({leak})")
    if case["fare_breakdown"] is not None:
        fb = case["fare_breakdown"]
        calc = (fb["base_fare"] + fb["distance_charge"] + fb["time_charge"] + fb["surge_amount"]
                + fb["erp_charges"] + fb["platform_fee"] - fb["promo_discount"]
                + fb.get("destination_change_fee", 0.0))
        if abs(calc - fb["total"]) > 0.015:
            errs.append(f"{cid}: fare lines sum to {calc:.2f}, total says {fb['total']}")
    return errs


def separation_checks(test_cases, prec_cases):
    """Nobody and no pickup venue may appear in both the test set and the precedents."""
    def sig(c):
        return dict(
            rider_id=c["rider_profile"]["rider_id"], driver_id=c["driver_profile"]["driver_id"],
            rider_name=c["rider_profile"]["name"], driver_name=c["driver_profile"]["name"],
            pickup=c["trip_data"]["pickup_location"]["name"])
    errs = []
    t_sigs = [sig(c) for c in test_cases]
    p_sigs = [sig(c) for c in prec_cases]
    for field in ("rider_id", "driver_id", "rider_name", "driver_name", "pickup"):
        both = {s[field] for s in t_sigs} & {s[field] for s in p_sigs}
        if both:
            errs.append(f"test set and precedents share {field}: {sorted(both)}")
    return errs


def policy_doc_in_sync():
    """The prose policy must quote the same numbers as params.json."""
    doc = open(os.path.join(ROOT, "policy", "ryde_dispute_policy.md"), encoding="utf-8").read()
    want = [
        f"**{PUB['free_wait_time_min']} minutes**", f"S${PUB['cancellation_fee_after_wait']:.2f}",
        f"**${PUB['driver_compensation']:.2f}**", f"**${PUB['waiting_fee']:.2f}**",
        f"**{PUB['advance_free_before_min']} minutes**",
        f"**{NSP['waiver_window_days']} days**",
        f"**{NSP['arrival_radius_m']} m**", f"**{NSP['late_driver_min']} minutes**",
        f"**{NSP['rider_on_way_extra_min']} minutes**",
        f"**{NSP['stalled_dist_m']} m**", f"**{NSP['stalled_min']} minutes**",
        f"**{NSP['invalid_tap_far_m']} m**", f"**{NSP['tap_good_faith_m']} m**",
        f"**{NSP['fraud_driver_warnings']} warnings**", f"**{NSP['new_account_days']} days**",
        f"**{NSP['fraud_rider_rejected']} rejected disputes**",
        f"**{int(RDP['tol_pct'] * 100)}% or {RDP['tol_km']:.1f} km",
        f"**{int(RDP['app_reroute_cap'] * 100)}%**",
        f"**${RDP['dest_change_fee']:.2f}**",
        f"base {FARE['base']:.2f} + {FARE['per_km']:.2f} per km + {FARE['per_min']:.2f} per min",
        f"platform fee {FARE['platform_fee']:.2f}",
        f"more than {RDP['stop_free_min']} minutes", f"more than {int(RDP['meter_mismatch'] * 100)}%",
        f"below {GEN['escalate_below_confidence']:.2f}",
        f"free_wait_time_min\": {PUB['free_wait_time_min']}",
        f"cancellation_fee_after_wait\": {PUB['cancellation_fee_after_wait']}",
        f"no_show_threshold_min\": {PUB['no_show_threshold_min']}",
        f"**{DMG['claim_deadline_h']} hours**", f"**{DMG['photo_window_after_trip_h']} hours**",
        f"**{DMG['ai_generated_threshold']:.2f}**",
        f"food, drink, groceries, crumbs or sand **S${DMG['caps']['food_drink']:.0f}**",
        f"**S${DMG['caps']['bodily_fluids']:.0f}**", f"vomit **S${DMG['caps']['vomit']:.0f}**",
        f"more than **{SAF['over_limit_consecutive_kmh']} km/h** over the limit on {SAF['consecutive_pings']} or more",
        f"more than **{SAF['over_limit_single_kmh']} km/h** over on any single ping",
        f"**{SAF['reporter_fraud_rejected']} rejected disputes** (G-10h)",
    ]
    return [f"policy doc does not contain '{w}' (params.json and the document disagree)"
            for w in want if w not in doc]


def chunk_checks():
    """Each policy section must fit one ADP knowledge slice (4,800 characters, split on '## '), and each past
    ruling one precedent slice (1,500 characters, split on '### ')."""
    errs = []
    doc = open(os.path.join(ROOT, "policy", "ryde_dispute_policy.md"), encoding="utf-8").read()
    for sec in re.split(r"(?m)^(?=## )", doc):
        if len(sec) > 4800:
            errs.append(f"policy section '{sec.splitlines()[0][:50]}' is {len(sec)} characters (> 4800)")
    pdir = os.path.join(ROOT, "precedents")
    for fn in sorted(os.listdir(pdir)):
        if fn.endswith(".md"):
            for sec in re.split(r"(?m)^(?=### )", open(os.path.join(pdir, fn), encoding="utf-8").read()):
                if len(sec) > 1500:
                    errs.append(f"{fn}: section '{sec.splitlines()[0][:40]}' is {len(sec)} characters (> 1500)")
    return errs


def ruling_format_checks(key, precs):
    errs = []
    ruling_schema = json.load(open(os.path.join(ROOT, "schema", "ruling_schema.json"), encoding="utf-8"))
    if ruling_schema["required"] != RULING_FIELDS:
        errs.append("schema/ruling_schema.json does not list exactly the fields in schema/ruling_fields.json")
    for k in key:
        if list(k["expected"]) != RULING_FIELDS:
            errs.append(f"{k['id']}: answer key fields differ from schema/ruling_fields.json")
        errs += [f"{k['id']} (key): {e}" for e in schema_errors(k["expected"], ruling_schema, "expected")]
        if k["expected"]["id"] != k["id"]:
            errs.append(f"{k['id']}: expected.id does not match")
    for pid, d in precs.items():
        if list(d["ruling"]) != RULING_FIELDS:
            errs.append(f"{pid}: ruling fields differ from schema/ruling_fields.json")
        errs += [f"{pid} (ruling): {e}" for e in schema_errors(d["ruling"], ruling_schema, "ruling")]
    return errs


def main():
    key, cases, precs = load()
    problems, rows = [], []
    for k in key:
        case = cases[k["id"]]
        problems += structure_checks(case)
        if case["dispute_ticket"]["dispute_type"] != k["category"]:
            problems.append(f"{k['id']}: key category {k['category']} differs from the case's dispute_type")
        d = derive(case)
        bad = compare(d, k["expected"], tolerance_for(k["expected"]["rules_cited"]))
        rows.append((k["id"], k["category"], not bad))
        problems += [f"{k['id']}: {b}" for b in bad]

    for pid, d in precs.items():
        case, ruling = d["case"], d["ruling"]
        problems += structure_checks(case)
        dd = derive(case)
        bad = compare(dd, ruling, tolerance_for(ruling["rules_cited"]))
        rows.append((pid, case["dispute_ticket"]["dispute_type"], not bad))
        problems += [f"{pid}: {b}" for b in bad]

    problems += separation_checks([cases[k["id"]] for k in key], [d["case"] for d in precs.values()])
    problems += policy_doc_in_sync()
    problems += ruling_format_checks(key, precs)
    problems += chunk_checks()

    by_id = {k["id"]: k for k in key}
    same = ("outcome", "refund_amount", "payer", "driver_warning", "escalate", "driver_goodwill_paid_by_ryde",
            "fraud_flag", "provisional_outcome", "rider_charge_amount", "rider_warning", "safety_referral")
    for k in key:
        if k["variant_of"]:  # same evidence, different people: identical ruling
            src = by_id[k["variant_of"]]["expected"]
            for f in same:
                if src[f] != k["expected"][f]:
                    problems.append(f"{k['id']}: variant differs from {k['variant_of']} on {f}")
        if k.get("contrast_of"):  # one changed fact: only the fraud review flag may differ
            src = by_id[k["contrast_of"]]["expected"]
            for f in same:
                if f != "fraud_flag" and src[f] != k["expected"][f]:
                    problems.append(f"{k['id']}: contrast differs from {k['contrast_of']} on {f}")
            if src["fraud_flag"] == k["expected"]["fraud_flag"]:
                problems.append(f"{k['id']}: contrast should differ from {k['contrast_of']} on fraud_flag")

    ids = [k["id"] for k in key] + list(precs)
    if len(ids) != len(set(ids)):
        problems.append("duplicate case ids")
    t_desc = {cases[k["id"]]["dispute_ticket"]["description"] for k in key}
    for pid, d in precs.items():
        if d["case"]["dispute_ticket"]["description"] in t_desc:
            problems.append(f"{pid}: same complaint text as a test case")

    ok = sum(1 for r in rows if r[2])
    print(f"cases derived from raw data and matched against the key: {ok}/{len(rows)}")
    by_cat = {}
    for r in rows:
        a = by_cat.setdefault(r[1], [0, 0])
        a[0] += r[2]
        a[1] += 1
    for c, (good, n) in by_cat.items():
        print(f"  {c}: {good}/{n}")
    for r in rows:
        if not r[2]:
            print("  MISMATCH", r[0])
    if problems:
        print(f"{len(problems)} problem(s):")
        for p in problems:
            print("  -", p)
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
