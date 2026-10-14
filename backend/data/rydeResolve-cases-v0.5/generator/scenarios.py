"""Turns scenario specs into built cases (case json, metrics, expected)."""
import copy
import json
import re

from builders import build_ns, build_rd
from trip_builder import build_trip
from lib import FARE, RD_POL, fare, money
from people import drivers, precedent_drivers, precedent_riders, riders


def resolve_amount(formula, case, m):
    if not isinstance(formula, str):
        return formula
    charged = case["fare_breakdown"]["total"]
    est = case["trip_data"]["upfront_estimate"]["total"]
    if formula == "excess":
        return money(charged - est)
    if formula == "stop_time":
        return money(m["stop_min"] * FARE["per_min"] * m["surge"])
    if formula == "promo":
        return case["trip_data"]["upfront_estimate"]["promo_discount"]
    if formula == "surge_diff":
        fb = case["fare_breakdown"]
        pre = fb["base_fare"] + fb["distance_charge"] + fb["time_charge"]
        quoted = case["trip_data"]["upfront_estimate"]["surge_multiplier"]
        return money(pre * (fb["surge_multiplier"] - quoted))
    if formula == "cap_excess":
        return money(charged - (1 + RD_POL["app_reroute_cap"]) * est)
    if formula == "meter":
        fb = case["fare_breakdown"]
        right = fare(m["actual_km"], fb["duration_min"], fb["surge_multiplier"], fb["erp_charges"],
                     fb["promo_discount"])
        return money(charged - right["total"])
    raise ValueError(formula)


def _pools():
    return {**riders(), **precedent_riders()}, {**drivers(), **precedent_drivers()}


_PLATE = re.compile(r"\(([A-Z]{2,3}) (\d{3,4}) ([A-Z])\)")


def _distinct_people(out):
    """An audit found the same rider/driver ID reused across cases with histories that never changed.
    Each later appearance of a pool person becomes a different person with the same name: a new ID and,
    for drivers, a different number plate (also replaced in that case's chat)."""
    seen = {}
    for r in sorted(out, key=lambda r: r["case"]["trip_data"].get("booked_at") or ""):
        c = r["case"]
        for role, pre in (("rider_profile", "rider_id"), ("driver_profile", "driver_id")):
            pid = c[role][pre]
            k = seen.get(pid, 0)
            seen[pid] = k + 1
            if k == 0:
                continue
            letter, num = pid.split("-")
            new_id = f"{letter}-{int(num) + 5000 * k}"
            text = json.dumps(c, ensure_ascii=False).replace(pid, new_id)
            if role == "driver_profile":
                m = _PLATE.search(c[role]["vehicle"])
                if m:
                    new_num = str((int(m.group(2)) * 7 + 1371 * k) % 9000 + 1000)
                    text = text.replace(f"{m.group(1)} {m.group(2)} {m.group(3)}",
                                        f"{m.group(1)} {new_num} {m.group(3)}")
            r["case"] = c = json.loads(text)
    return out


# v0.5: values for the three new ruling fields in cases written before they existed. Listed here so the
# change is visible; tools/validate.py derives the same values independently from the case data.
SAFETY_ESCALATIONS = {  # escalated over a safety concern (G-4, SF-1): Ryde's safety team must see them
    "DISP-T-NS-33": ["SF-1"],   # rider threatened the driver in chat
    "DISP-T-NS-41": [],         # car did not match the app (NS-15 gap, a safety concern)
    "DISP-T-RD-20": ["SF-1"],   # rider asked to be let out and the driver refused
}


def _v05_fields(r):
    e = r["expected"]
    c = r["case"]
    if r["kind"] == "no_show" and c["dispute_ticket"]["filed_by"] == "driver" and e["outcome"] == "charge_upheld":
        # a driver's upheld claim for an unapplied fee charges the rider the block's fee now (NS-12, G-6)
        e["rider_charge_amount"] = c["cancellation_policy"]["cancellation_fee_after_wait"]
    if r["id"] in SAFETY_ESCALATIONS:
        e["safety_referral"] = True
        e["rules"] = e["rules"] + [x for x in SAFETY_ESCALATIONS[r["id"]] if x not in e["rules"]]


def build_all(specs_ns, specs_rd, specs_trip=()):
    out = []
    for sp in specs_ns:
        R, D = _pools()
        case, metrics = build_ns(sp["id"], rider=copy.deepcopy(R[sp["rider"]]),
                                 driver=copy.deepcopy(D[sp["driver"]]), **sp["kw"])
        exp = copy.deepcopy(sp["expected"])
        out.append(dict(id=sp["id"], set=sp["set"], tags=sp["tags"], kind="no_show", case=case,
                        metrics=metrics, expected=exp, title=sp["kw"]["title"],
                        variant_of=sp.get("variant_of"), contrast_of=sp.get("contrast_of")))
    for sp in specs_rd:
        R, D = _pools()
        case, metrics = build_rd(sp["id"], rider=copy.deepcopy(R[sp["rider"]]),
                                 driver=copy.deepcopy(D[sp["driver"]]), **sp["kw"])
        exp = copy.deepcopy(sp["expected"])
        exp["refund_amount"] = resolve_amount(exp["refund_amount"], case, metrics)
        out.append(dict(id=sp["id"], set=sp["set"], tags=sp["tags"], kind="route_deviation", case=case,
                        metrics=metrics, expected=exp, title=sp["kw"]["title"],
                        variant_of=sp.get("variant_of"), contrast_of=sp.get("contrast_of")))
    for sp, category in specs_trip:
        R, D = _pools()
        kw = {k: v for k, v in sp["kw"].items()}
        case, metrics = build_trip(sp["id"], category=category, rider=copy.deepcopy(R[sp["rider"]]),
                                   driver=copy.deepcopy(D[sp["driver"]]), **kw)
        exp = copy.deepcopy(sp["expected"])
        if exp["refund_amount"] == "fare":
            exp["refund_amount"] = case["fare_breakdown"]["total"]
        out.append(dict(id=sp["id"], set=sp["set"], tags=sp["tags"], kind=category, case=case,
                        metrics=metrics, expected=exp, title=sp["kw"]["title"],
                        variant_of=sp.get("variant_of"), contrast_of=sp.get("contrast_of")))
    for r in out:
        _v05_fields(r)
    return _distinct_people(out)
