"""Shared helpers for generating RydeResolve dispute cases.

All derived facts (distances, wait times, fares) are computed here so the raw
evidence in each case is internally consistent.
"""
import json
import math
import os
import random
from datetime import datetime, timedelta, timezone

SGT = timezone(timedelta(hours=8))

# Every policy number lives in policy/params.json. Do not hardcode them anywhere else.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(ROOT, "policy", "params.json"), encoding="utf-8") as _f:
    PARAMS = json.load(_f)

POLICY_VERSION = "ryde-policy-v0.4"
FARE = PARAMS["fare"]
NS_POL = PARAMS["no_show"]
RD_POL = PARAMS["route"]
PROFILES = PARAMS["profiles"]  # the two cancellation_policy blocks a no-show case may carry

PLACES = {
    "bugis":      ("Bugis Junction (Victoria St taxi stand)", 1.29935, 103.85480, False),
    "tampines":   ("Tampines Mall (Tampines Central 5 drop-off)", 1.35245, 103.94460, False),
    "toapayoh79": ("Blk 79 Toa Payoh Lor 1 (void deck)", 1.33430, 103.84990, False),
    "amk":        ("Ang Mo Kio Hub (Ang Mo Kio Ave 3 pickup bay)", 1.36930, 103.84860, False),
    "orchard":    ("ION Orchard (Orchard Turn pickup point)", 1.30400, 103.83180, False),
    "jem":        ("JEM, Jurong East", 1.33330, 103.74300, True),
    "paya":       ("Paya Lebar Quarter (Mall drop-off)", 1.31700, 103.89300, False),
    "hillview":   ("Hillview Grove Condominium (lobby)", 1.36210, 103.76420, False),
    "raffles":    ("Raffles Place (Chulia St taxi stand)", 1.28400, 103.85150, False),
    "kallang":    ("Kallang Wave Mall", 1.30200, 103.87500, False),
    "serangoon":  ("NEX, Serangoon Central", 1.35070, 103.87230, False),
    "punggol":    ("Waterway Point, Punggol", 1.40650, 103.90220, False),
    "woodlands":  ("Causeway Point, Woodlands", 1.43600, 103.78600, False),
    "yishun":     ("Northpoint City, Yishun", 1.42950, 103.83600, False),
    "bishan":     ("Junction 8, Bishan", 1.35040, 103.84850, False),
    "clementi":   ("Clementi Mall", 1.31500, 103.76500, False),
    "holland":    ("Holland Village (Lorong Liput)", 1.31100, 103.79600, False),
    "mbs":        ("Marina Bay Sands (Hotel Tower 1 lobby)", 1.28340, 103.86070, False),
    "changi":     ("Changi Airport Terminal 3 (Departures)", 1.35550, 103.98640, False),
    "changi_arr": ("Changi Airport Terminal 3 (Arrival pickup point)", 1.35570, 103.98620, False),
    "suntec":     ("Suntec City (Tower 3 taxi stand)", 1.29500, 103.85800, False),
    "cbp":        ("Changi Business Park Central 1", 1.33400, 103.96400, False),
    "utown":      ("NUS University Town (Stephen Riady Centre)", 1.30480, 103.77350, False),
    "onenorth":   ("Fusionopolis, one-north", 1.29900, 103.78760, False),
    "tiongbahru": ("Tiong Bahru Plaza", 1.28620, 103.82700, False),
    "vivocity":   ("VivoCity", 1.26480, 103.82230, False),
    "westgate":   ("Westgate, Jurong East", 1.33430, 103.74270, True),
    # Venues used only by the precedents, so the test set never shares a pickup with them.
    "bedok":      ("Bedok Mall (Bedok Central drop-off)", 1.32430, 103.93000, False),
    "sengkang":   ("Compass One, Sengkang", 1.39200, 103.89500, False),
    "bukitpanjang": ("Hillion Mall, Bukit Panjang", 1.37780, 103.76230, False),
    "novena":     ("Velocity@Novena Square", 1.32030, 103.84380, False),
    "tanjongpagar": ("Tanjong Pagar Centre", 1.27620, 103.84660, False),
    "plazasing":  ("Plaza Singapura", 1.30020, 103.84520, True),
    "sembawang":  ("Sun Plaza, Sembawang", 1.44870, 103.81970, False),
    "bukitbatok": ("West Mall, Bukit Batok", 1.34980, 103.74960, False),
    "jurongpoint": ("Jurong Point", 1.33970, 103.70670, False),
    "pasirris":   ("White Sands, Pasir Ris", 1.37270, 103.94930, False),
    "anchorpoint": ("Anchorpoint, Queenstown", 1.28890, 103.80860, False),
}


def T(s):
    return datetime.fromisoformat(s).replace(tzinfo=SGT)


def iso(t):
    return t.isoformat(timespec="seconds")


def hav(a, b):
    """Great-circle distance in km between (lat, lng) pairs."""
    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)
    d = (math.sin((lat2 - lat1) / 2) ** 2
         + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2)
    return 2 * 6371.0088 * math.asin(math.sqrt(d))


def move(p, dist_m, bearing_deg):
    lat, lon = map(math.radians, p)
    br = math.radians(bearing_deg)
    d = dist_m / 6371008.8
    lat2 = math.asin(math.sin(lat) * math.cos(d) + math.cos(lat) * math.sin(d) * math.cos(br))
    lon2 = lon + math.atan2(math.sin(br) * math.sin(d) * math.cos(lat),
                            math.cos(d) - math.sin(lat) * math.sin(lat2))
    return (math.degrees(lat2), math.degrees(lon2))


def lerp(a, b, f):
    return (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)


def bearing(a, b):
    lat1, lat2 = math.radians(a[0]), math.radians(b[0])
    dl = math.radians(b[1] - a[1])
    y = math.sin(dl) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dl)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


# Road model. Real roads are longer than the straight line between two points: an audit found that
# planned routes equal to the straight-line distance were physically impossible. A planned route is now
# a two-leg path about ROAD_FACTOR times the straight line, kept on land.
ROAD_FACTOR = 1.28

# A rough outline of Singapore's main island (lat, lng). Only used to keep routes off the sea.
LAND = [(1.300, 103.640), (1.340, 103.655), (1.420, 103.700), (1.445, 103.745), (1.455, 103.790),
        (1.468, 103.820), (1.445, 103.860), (1.420, 103.905), (1.395, 103.940), (1.390, 103.985),
        (1.355, 104.030), (1.320, 103.990), (1.312, 103.945), (1.300, 103.910), (1.288, 103.875),
        (1.272, 103.860), (1.262, 103.840), (1.262, 103.810), (1.278, 103.780), (1.298, 103.745)]


def on_land(p):
    lat, lng = p
    inside, n = False, len(LAND)
    for i in range(n):
        (y1, x1), (y2, x2) = LAND[i], LAND[(i + 1) % n]
        if (y1 > lat) != (y2 > lat):
            x = x1 + (lat - y1) * (x2 - x1) / (y2 - y1)
            if lng < x:
                inside = not inside
    return inside


def path_on_land(points, step_m=150):
    for a, b in zip(points, points[1:]):
        n = max(1, int(hav(a, b) * 1000 / step_m))
        for i in range(n + 1):
            if not on_land(lerp(a, b, i / n)):
                return False
    return True


def _via(a, b, target_km, f, side):
    d = hav(a, b)
    lo, hi = 0.0, d * 2
    base = lerp(a, b, f)
    perp = (bearing(a, b) + 90 * side) % 360
    for _ in range(60):
        mid = (lo + hi) / 2
        via = move(base, mid * 1000, perp)
        if hav(a, via) + hav(via, b) < target_km:
            lo = mid
        else:
            hi = mid
    return move(base, ((lo + hi) / 2) * 1000, perp)


def road_side(pickup, dropoff):
    a, b = ppos(pickup), ppos(dropoff)
    d = hav(a, b)
    for side in (1, -1):
        if path_on_land([a, _via(a, b, d * ROAD_FACTOR, 0.5, side), b]):
            return side
    return 1


def road_via(pickup, dropoff):
    """The single via point of the app's planned route between two places."""
    a, b = ppos(pickup), ppos(dropoff)
    return _via(a, b, hav(a, b) * ROAD_FACTOR, 0.5, road_side(pickup, dropoff))


def detour(pickup, dropoff, pct, f=0.5, side=None):
    """One via point that makes the driven route `pct` percent longer than the planned route
    (which is itself ROAD_FACTOR times the straight line). Kept on land: if the requested side
    would cross the sea, the other side is used."""
    a, b = ppos(pickup), ppos(dropoff)
    target = hav(a, b) * ROAD_FACTOR * (1 + pct / 100.0)
    side = road_side(pickup, dropoff) if side is None else side
    for s in (side, -side):
        via = _via(a, b, target, f, s)
        if path_on_land([a, via, b]):
            return via
    # A long detour cannot be one bend without leaving the island: use a two-bend path instead.
    for fr in ((0.25, 0.75), (0.15, 0.55), (0.45, 0.85), (0.1, 0.4), (0.6, 0.9)):
        for s in (side, -side):
            pts = _two_bend(a, b, target, s, fr)
            if path_on_land([a] + pts + [b]):
                return Path(pts)
    raise ValueError(f"no on-land detour for {pickup}->{dropoff} at {pct}%")


class Path(list):
    """Several via points returned by detour(); build_rd splices them into the driven route."""


def _two_bend(a, b, target_km, side, fr=(0.25, 0.75)):
    perp = (bearing(a, b) + 90 * side) % 360
    p1, p2 = lerp(a, b, fr[0]), lerp(a, b, fr[1])
    lo, hi = 0.0, hav(a, b) * 2
    for _ in range(60):
        mid = (lo + hi) / 2
        q1, q2 = move(p1, mid * 1000, perp), move(p2, mid * 1000, perp)
        if hav(a, q1) + hav(q1, q2) + hav(q2, b) < target_km:
            lo = mid
        else:
            hi = mid
    h = (lo + hi) / 2 * 1000
    return [move(p1, h, perp), move(p2, h, perp)]


class OnLine(tuple):
    """A point a fraction `f` along the planned route. build_rd expands it so the driven path
    follows the planned route up to that point."""
    f = 0.0


def on_line(pickup, dropoff, f):
    a, b, v = ppos(pickup), ppos(dropoff), road_via(pickup, dropoff)
    l1, l2 = hav(a, v), hav(v, b)
    s = f * (l1 + l2)
    p = lerp(a, v, s / l1) if s <= l1 else lerp(v, b, (s - l1) / l2)
    out = OnLine(p)
    out.f = f
    return out


def latlng(p, nd=6):
    return {"lat": round(p[0], nd), "lng": round(p[1], nd)}


def money(x):
    return round(x + 1e-9, 2)


def place(key):
    name, lat, lng, multi = PLACES[key]
    return {"name": name, "lat": lat, "lng": lng, "multi_entrance_venue": multi}


def ppos(key):
    _, lat, lng, _ = PLACES[key]
    return (lat, lng)


def poly_km(points):
    return sum(hav(points[i], points[i + 1]) for i in range(len(points) - 1))


def fare(km, minutes, surge=1.0, erp=0.0, promo=0.0):
    # Round the displayed quantities first, so every line on the receipt can be recomputed exactly
    # from the numbers shown on it (an audit found 1-2 cent gaps when this was done the other way).
    km, minutes = round(km, 2), round(minutes, 1)
    base = FARE["base"]
    dist = money(km * FARE["per_km"])
    tm = money(minutes * FARE["per_min"])
    pre = base + dist + tm
    surge_amt = money(pre * (surge - 1.0))
    total = money(pre + surge_amt + erp + FARE["platform_fee"] - promo)
    return {
        "base_fare": base,
        "distance_km": round(km, 2),
        "distance_charge": dist,
        "duration_min": round(minutes, 1),
        "time_charge": tm,
        "surge_multiplier": surge,
        "surge_amount": surge_amt,
        "erp_charges": money(erp),
        "platform_fee": FARE["platform_fee"],
        "promo_discount": money(promo),
        "total": total,
    }


def rider(rid, name, *, age, lang="English", access=None, channel="email", acct=400,
          trips=60, rating=4.7, disputes=(0, 0, 0), flags=0, flag_details=None,
          pay="e-wallet"):
    t, u, r = disputes
    return {
        "rider_id": rid, "name": name, "account_age_days": acct, "total_trips": trips,
        "avg_rating": rating,
        "dispute_history": {"total_disputes": t, "upheld": u, "rejected": r},
        "fraud_flags": flags, "fraud_flag_details": flag_details,
        "payment_method": pay,
        "age_years": age,
        "communication_preferences": {
            "preferred_language": lang,
            "accessibility_needs": access,
            "channel": channel,
        },
    }


def driver(did, name, *, vehicle, age=40, lang="English", access=None, channel="in_app",
           acct=900, trips=2500, rating=4.8, disputes=(0, 0, 0), flags=0, flag_details=None,
           warnings_30d=0):
    t, u, r = disputes
    return {
        "driver_id": did, "name": name, "account_age_days": acct, "total_trips": trips,
        "avg_rating": rating,
        "dispute_history": {"total_disputes": t, "upheld_against": u, "rejected": r},
        "fraud_flags": flags, "fraud_flag_details": flag_details,
        "warnings_last_30_days": warnings_30d,
        "vehicle": vehicle,
        "age_years": age,
        "communication_preferences": {
            "preferred_language": lang,
            "accessibility_needs": access,
            "channel": channel,
        },
    }


def rng_for(cid):
    return random.Random(cid)
