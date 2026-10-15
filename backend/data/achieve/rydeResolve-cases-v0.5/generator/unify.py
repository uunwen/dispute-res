"""One case format for every dispute type (v0.5).

Every case file has exactly the same keys at every level. A section that does not apply to a dispute
type is null (an object) or [] (a list); it is never missing. CASE_SPEC below is the single definition:
normalize() fills each built case against it and refuses unknown keys, and json_schema() writes the same
definition out as schema/case_schema.json (JSON Schema draft-07) for teammates and tools.

Spec notation: a dict is an object with exactly these keys; ("list", spec) is a list of items;
("nullable", spec) may also be null; a tuple of type names lists the allowed JSON types.
"""
import copy

S, N, I, B = ("string",), ("number",), ("integer",), ("boolean",)
SN, NN, IN, BN = ("string", "null"), ("number", "null"), ("integer", "null"), ("boolean", "null")

LOCATION = {"name": S, "lat": N, "lng": N, "multi_entrance_venue": B}
LATLNG = {"lat": N, "lng": N}
FARE_LINES = {"base_fare": N, "distance_km": N, "distance_charge": N, "duration_min": N, "time_charge": N,
              "surge_multiplier": N, "surge_amount": N, "erp_charges": N, "platform_fee": N,
              "promo_discount": N, "total": N}
PROFILE_COMMON = {"account_age_days": I, "total_trips": I, "avg_rating": N}
COMM = {"preferred_language": S, "accessibility_needs": SN, "channel": S}

CASE_SPEC = {
    "dispute_ticket": {"dispute_id": S, "trip_id": S, "filed_by": S, "dispute_type": S, "description": S,
                       "filed_at": S, "status": S},
    "rider_profile": {"rider_id": S, "name": S, **PROFILE_COMMON,
                      "dispute_history": {"total_disputes": I, "upheld": I, "rejected": I},
                      "fraud_flags": I, "fraud_flag_details": SN, "payment_method": S, "age_years": I,
                      "communication_preferences": COMM},
    "driver_profile": {"driver_id": S, "name": S, **PROFILE_COMMON,
                       "dispute_history": {"total_disputes": I, "upheld_against": I, "rejected": I},
                       "fraud_flags": I, "fraud_flag_details": SN, "warnings_last_30_days": I, "vehicle": S,
                       "age_years": I, "communication_preferences": COMM},
    "trip_data": {
        "trip_id": S, "rider_id": S, "driver_id": S, "pickup_location": LOCATION, "dropoff_location": LOCATION,
        "trip_type": S, "booked_at": S, "matched_at": SN, "scheduled_time": SN, "eta_at_assignment_min": IN,
        "driver_arrival_time": SN, "driver_wait_start": SN, "cancellation_time": SN, "cancelled_by": SN,
        "cancellation_reason": SN, "cancellation_fee": NN, "waiting_fee": NN, "payment_status": S,
        "trip_start": SN, "trip_end": SN, "trip_completed": B,
        "planned_route": ("nullable", {"distance_km": N, "duration_min": N, "waypoints": ("list", LATLNG),
                                       "erp_gantries": ("list", {"gantry": S, "charge": N})}),
        "upfront_estimate": ("nullable", FARE_LINES),
        "damage_claim": ("nullable", {"claim_id": S, "submitted_at": S, "mess_type_claimed": S,
                                      "amount_claimed": N, "attachment_ids": ("list", S), "status": S,
                                      "amount_charged": N}),
    },
    "cancellation_policy": ("nullable", {
        "free_wait_time_min": I, "cancellation_fee_after_wait": N, "no_show_threshold_min": I,
        "fee_goes_to": S, "driver_compensation": NN, "waiting_fee": NN, "driver_waiting_fee": NN,
        "advance_free_before_min": IN}),
    "fare_breakdown": ("nullable", {**FARE_LINES, "promo_code": SN,
                                    "erp_gantries_passed": ("list", {"gantry": S, "charge": N}),
                                    "destination_change_fee": N}),
    "gps_telemetry": ("list", {"timestamp": S, "lat": N, "lng": N, "speed_kmh": I, "accuracy_m": N,
                               "status": S, "speed_limit_kmh": IN}),
    "rider_app_location": ("nullable", {"available": B, "note": SN,
                                        "pings": ("list", {"timestamp": S, "lat": N, "lng": N, "accuracy_m": N})}),
    "chat_logs": ("list", {"timestamp": S, "sender": S, "type": S, "content": S}),
    "app_events": ("list", {"timestamp": S, "event_type": S, "details": S}),
    "traffic_incidents": ("nullable", {
        "source": S, "query_window": ("list", S),
        "incidents": ("list", {"incident_id": S, "type": S, "road": S, "description": S, "severity": S,
                               "location": LATLNG, "reported_at": S, "cleared_at": S})}),
    "attachments": ("list", {
        "attachment_id": S, "attachment_type": S, "uploaded_by": S, "uploaded_at": S, "captured_at": S,
        "location": ("nullable", LATLNG), "file_hash": S,
        "simulated_vision_analysis": ("nullable", {
            "note": S, "description": S, "mess_type": S, "severity": S, "plate_read": SN,
            "interior_matches_vehicle_model": B, "ai_generated_likelihood": N, "duplicate_of": SN}),
        "receipt_details": ("nullable", {
            "company_name": S, "uen": SN, "address": SN, "contact_number": SN, "service_description": S,
            "professional_cleaning": B, "cleaning_date": S, "car_plate": SN, "amount": N, "signed": B,
            "company_stamp": B})}),
    "policy_ref": S,
}

DISPUTE_TYPES = ("no_show_charge", "route_deviation", "property_damage", "safety_incident")


def _event(case, typ):
    return next((e["timestamp"] for e in case["app_events"] if e["event_type"] == typ), None)


def _prepare(case):
    """Bring the older builders' output to the shared shape before the strict fill."""
    c = copy.deepcopy(case)
    td = c["trip_data"]
    dtype = c["dispute_ticket"]["dispute_type"]
    if dtype == "no_show_charge":
        rl = c.get("rider_app_location")
        if isinstance(rl, list):
            c["rider_app_location"] = {"available": True, "note": None, "pings": rl}
        elif isinstance(rl, dict) and "pings" not in rl:
            c["rider_app_location"] = {"available": bool(rl.get("available")), "note": rl.get("note"), "pings": []}
        blk = c.get("cancellation_policy")
        if blk is not None:
            c["cancellation_policy"] = {k: blk.get(k) for k in CASE_SPEC["cancellation_policy"][1]}
        td.setdefault("trip_start", _event(c, "trip_started"))
        td.setdefault("trip_end", _event(c, "trip_completed"))
    else:
        c.setdefault("rider_app_location", None)
        c.setdefault("cancellation_policy", None)
        td.setdefault("trip_type", "on_demand")
        td.setdefault("matched_at", _event(c, "driver_assigned"))
        td.setdefault("payment_status", "captured")
        td.setdefault("trip_completed", True)
        td.setdefault("driver_arrival_time", _event(c, "driver_arrived"))
        td.setdefault("driver_wait_start", _event(c, "driver_arrived"))
        fb = c.get("fare_breakdown")
        if fb is not None:
            fb.setdefault("destination_change_fee", 0.0)
    for g in c["gps_telemetry"]:
        g.setdefault("speed_limit_kmh", None)
    c.setdefault("traffic_incidents", None)
    c.setdefault("attachments", [])
    c.setdefault("fare_breakdown", None)
    return c


def _fill(value, spec, path):
    """Return value shaped exactly like spec: missing keys become null/[], unknown keys are an error."""
    if isinstance(spec, tuple) and spec and spec[0] == "nullable":
        return None if value is None else _fill(value, spec[1], path)
    if isinstance(spec, tuple) and spec and spec[0] == "list":
        if value is None:
            value = []
        if not isinstance(value, list):
            raise ValueError(f"{path}: expected a list")
        return [_fill(v, spec[1], path + "[]") for v in value]
    if isinstance(spec, dict):
        if not isinstance(value, dict):
            raise ValueError(f"{path}: expected an object, got {type(value).__name__}")
        extra = set(value) - set(spec)
        if extra:
            raise ValueError(f"{path}: keys not in the case format: {sorted(extra)}")
        out = {}
        for k, sub in spec.items():
            v = value.get(k)
            if v is None and isinstance(sub, tuple) and sub and sub[0] == "list":
                v = []
            out[k] = _fill(v, sub, f"{path}.{k}")
        return out
    return value  # a leaf; types are checked by tools/validate.py against schema/case_schema.json


def normalize(case):
    return _fill(_prepare(case), CASE_SPEC, "case")


def json_schema():
    def conv(spec):
        if isinstance(spec, tuple) and spec and spec[0] == "nullable":
            inner = conv(spec[1])
            return {"anyOf": [inner, {"type": "null"}]}
        if isinstance(spec, tuple) and spec and spec[0] == "list":
            return {"type": "array", "items": conv(spec[1])}
        if isinstance(spec, dict):
            return {"type": "object", "additionalProperties": False, "required": list(spec),
                    "properties": {k: conv(v) for k, v in spec.items()}}
        return {"type": list(spec) if len(spec) > 1 else spec[0]}
    sch = conv(CASE_SPEC)
    sch["properties"]["dispute_ticket"]["properties"]["dispute_type"] = {"enum": list(DISPUTE_TYPES)}
    sch["properties"]["dispute_ticket"]["properties"]["filed_by"] = {"enum": ["rider", "driver"]}
    return {"$schema": "http://json-schema.org/draft-07/schema#",
            "title": "RydeResolve dispute case (v0.5, one format for all four dispute types)",
            "description": "Every key is required in every case. A section that does not apply to a dispute "
                           "type is null (object) or [] (list). See schema/case_format.md.",
            **sch}
