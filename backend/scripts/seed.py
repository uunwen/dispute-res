import asyncio
import datetime as dt
import json
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text

from app.db import models
from app.db.enums import AccountRole, DisputeCategory
from app.db.session import async_session_factory

SEED = 42
RNG = random.Random(SEED)

BASE_TIME = dt.datetime(2026, 1, 12, 8, 0, 0, tzinfo=dt.timezone.utc)

BASE_FARE = 3.00
PER_KM_RATE = 0.90
PER_MIN_RATE = 0.30
CANCELLATION_FEE = 6.00

RIDER_NAMES = [
    "Aisha Tan", "Wei Ming Lim", "Priya Nair", "Marcus Lee", "Siti Rahman",
    "Jia Hao Ng", "Emily Chua", "Ravi Kumar", "Nurul Hassan", "Daniel Teo",
]
DRIVER_NAMES = [
    "Kumaravel Raj", "Boon Kiat Goh", "Farid Abdullah", "Melissa Wong",
    "Chong Wei Chen", "Arul Subramaniam", "Hui Ling Poh", "Mohammed Faiz",
    "Teng Seng Lim", "Joseph Pereira",
]
RIDER_RATINGS = [4.8, 4.5, 4.7, 4.3, 4.9, 4.6, 4.4, 4.2, 4.8, 3.4]
DRIVER_RATINGS = [4.7, 4.4, 4.6, 4.5, 4.3, 4.8, 4.2, 4.6, 4.1, 3.2]
RIDER_AGE_BANDS = ["25-34", "18-24", "35-44", "45-54", None, "25-34", "35-44", None, "55+", "25-34"]
DRIVER_AGE_BANDS = ["35-44", "25-34", "45-54", "25-34", "35-44", "55+", "18-24", "35-44", "45-54", "25-34"]

DATA_DIR = Path(__file__).resolve().parents[1] / "data"

SPECS = [
    ("A", "route_deviation", 0, 1),
    ("A", "route_deviation", 1, 9),
    ("A", "route_deviation", 2, 3),
    ("A", "route_deviation", 3, 9),
    ("A", "route_deviation", 9, 5),
    ("A", "route_deviation", 9, 6),
    ("B", "legit_detour", 5, 7),
    ("B", "legit_detour", 6, 8),
    ("B", "legit_detour", 9, 0),
    ("B", "legit_detour", 8, 1),
    ("C", "driver_no_show", 0, 2),
    ("C", "driver_no_show", 1, 4),
    ("C", "driver_no_show", 2, 7),
    ("C", "driver_no_show", 3, 8),
    ("C", "driver_no_show", 4, 0),
    ("C", "driver_no_show", 9, 3),
    ("D", "rider_no_show", 6, 1),
    ("D", "rider_no_show", 7, 2),
    ("D", "rider_no_show", 8, 4),
    ("D", "rider_no_show", 9, 5),
    ("E", "surge_mismatch", 4, 6),
    ("E", "surge_mismatch", 9, 8),
    ("E", "surge_mismatch", 7, 0),
    ("F", "frivolous", 9, 7),
    ("F", "frivolous", 9, 3),
    ("F", "repeated_deviation", 5, 9),
]

CATEGORY = {
    "route_deviation": DisputeCategory.route_deviation,
    "legit_detour": DisputeCategory.route_deviation,
    "driver_no_show": DisputeCategory.no_show,
    "rider_no_show": DisputeCategory.no_show,
    "surge_mismatch": DisputeCategory.fare_dispute,
    "frivolous": DisputeCategory.route_deviation,
    "repeated_deviation": DisputeCategory.route_deviation,
}

PRIORITY = {
    "route_deviation": "high",
    "legit_detour": "medium",
    "driver_no_show": "high",
    "rider_no_show": "medium",
    "surge_mismatch": "high",
    "frivolous": "low",
    "repeated_deviation": "high",
}

CLAIM_TEXT = {
    "route_deviation": "Driver deviated significantly from the optimal route without justification.",
    "legit_detour": "Rider claims route deviation, but driver took a justified detour due to a road closure.",
    "driver_no_show": "Driver never arrived at the pickup point and the rider was charged a cancellation fee.",
    "rider_no_show": "Rider disputes the cancellation fee, claiming they were present.",
    "surge_mismatch": "Rider was charged a surge multiplier that did not apply at booking time.",
    "frivolous": "Rider filed a dispute with no evidence of any service issue.",
    "repeated_deviation": "Driver repeatedly deviated from the route, adding significant distance.",
}


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


def lerp(p, q, t):
    return (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t)


def jitter(p, meters, rng):
    lat, lng = p
    dlat = rng.uniform(-1, 1) * meters / 111000.0
    dlng = rng.uniform(-1, 1) * meters / (111000.0 * math.cos(math.radians(lat)))
    return (lat + dlat, lng + dlng)


def route_length(points):
    total = 0.0
    for i in range(len(points) - 1):
        total += haversine_km(points[i], points[i + 1])
    return total


def random_point(rng):
    return (rng.uniform(1.28, 1.42), rng.uniform(103.65, 104.00))


def random_endpoints(rng, lo=3.0, hi=8.0):
    pickup = random_point(rng)
    while True:
        dropoff = random_point(rng)
        d = haversine_km(pickup, dropoff)
        if lo <= d <= hi:
            return pickup, dropoff


def make_optimal_route(pickup, dropoff, rng):
    d = haversine_km(pickup, dropoff)
    n = max(3, int(d * 4) + 2)
    mid = lerp(pickup, dropoff, 0.5)
    dx = dropoff[1] - pickup[1]
    dy = dropoff[0] - pickup[0]
    length = math.hypot(dx, dy) or 1.0
    perp = (-dy / length, dx / length)
    off = rng.uniform(-0.8, 0.8)
    dlat = perp[0] * (off / 111.0)
    dlng = perp[1] * (off / (111.0 * math.cos(math.radians(mid[0]))))
    mid = (mid[0] + dlat, mid[1] + dlng)
    pts = []
    for i in range(n):
        t = i / (n - 1)
        a = lerp(pickup, mid, t)
        b = lerp(mid, dropoff, t)
        pts.append(lerp(a, b, t))
    return pts


def simulate_drive(waypoints, speeds, dt_seconds, start, rng):
    if not waypoints:
        return [], 0.0
    pts = [(waypoints[0][0], waypoints[0][1], start, speeds[0] if speeds else 0.0)]
    t = 0.0
    for i in range(len(waypoints) - 1):
        a, b = waypoints[i], waypoints[i + 1]
        seg_km = haversine_km(a, b)
        speed = speeds[i]
        if seg_km < 1e-6 or speed <= 0:
            continue
        dur_s = seg_km / speed * 3600.0
        n = max(1, int(round(dur_s / dt_seconds)))
        step_s = dur_s / n
        for k in range(1, n + 1):
            pos = jitter(lerp(a, b, k / n), 12.0, rng)
            ts = start + dt.timedelta(seconds=t + k * step_s)
            spd = round(max(0.0, speed * (1 + rng.uniform(-0.08, 0.08))), 1)
            pts.append((pos[0], pos[1], ts, spd))
        t += dur_s
    return pts, t


def normal_waypoints(optimal, rng):
    return [jitter(p, 15.0, rng) for p in optimal]


def deviation_waypoints(optimal, rng):
    n = len(optimal)
    m1 = max(1, int(n * 0.40))
    m2 = min(n - 1, int(n * 0.78))
    a, b = optimal[m1], optimal[m2]
    dx, dy = b[1] - a[1], b[0] - a[0]
    length = math.hypot(dx, dy) or 1.0
    perp = (-dy / length, dx / length)
    mid = optimal[int(n * 0.55)]
    off = rng.uniform(2.8, 4.5)
    dlat = perp[0] * (off / 111.0)
    dlng = perp[1] * (off / (111.0 * math.cos(math.radians(mid[0]))))
    detour = (mid[0] + dlat, mid[1] + dlng)
    pts = [jitter(p, 15.0, rng) for p in optimal]
    return pts[:m1] + [detour] + pts[m2:]


def legit_detour_route(optimal, rng):
    n = len(optimal)
    m1 = max(1, int(n * 0.30))
    m2 = int(n * 0.55)
    m3 = min(n - 1, int(n * 0.85))
    mid = optimal[int(n * 0.40)]
    a, b = optimal[m1], optimal[m2]
    dx, dy = b[1] - a[1], b[0] - a[0]
    length = math.hypot(dx, dy) or 1.0
    perp = (-dy / length, dx / length)
    off = rng.uniform(0.5, 0.9)
    dlat = perp[0] * (off / 111.0)
    dlng = perp[1] * (off / (111.0 * math.cos(math.radians(mid[0]))))
    detour = (mid[0] + dlat, mid[1] + dlng)

    pts = [jitter(p, 12.0, rng) for p in optimal]
    wps = list(pts[:m2]) + [detour] + list(pts[m3:])
    speeds = []
    for i in range(m2 - 1):
        speeds.append(rng.uniform(7, 10) if i >= m1 - 1 else rng.uniform(24, 30))
    speeds.append(rng.uniform(28, 34))
    speeds.append(rng.uniform(28, 34))
    for _ in range(len(pts[m3:]) - 1):
        speeds.append(rng.uniform(24, 30))
    return wps, speeds


def driver_no_show_gps(pickup, start, rng):
    wrong = jitter(pickup, 450.0, rng)
    while haversine_km(wrong, pickup) < 0.15:
        wrong = jitter(pickup, 450.0, rng)
    pts = []
    for i in range(14):
        pos = jitter(wrong, 70.0, rng)
        if haversine_km(pos, pickup) < 0.12:
            pos = jitter(pos, 150.0, rng)
        spd = 0.0 if i % 4 == 0 else round(rng.uniform(8, 22), 1)
        ts = start + dt.timedelta(seconds=25 * i)
        pts.append((pos[0], pos[1], ts, spd))
    return pts


def rider_no_show_gps(pickup, start, rng, wait_min=6.0):
    startpt = jitter(pickup, 1800.0, rng)
    approach, dur = simulate_drive([startpt, pickup], [30.0], 20.0, start, rng)
    pts = list(approach)
    arrival = start + dt.timedelta(seconds=dur)
    for s in range(20, int(wait_min * 60) + 1, 20):
        pos = jitter(pickup, 4.0, rng)
        pts.append((pos[0], pos[1], arrival + dt.timedelta(seconds=s), 0.0))
    return pts, arrival


def chat_for(label, rider_name, driver_name, est, actual):
    if label == "route_deviation":
        return [
            ("rider", "Hi, why are we going so far off the route?"),
            ("driver", "Sorry, I think I missed a turn."),
            ("rider", "This is adding a lot of time."),
            ("driver", "I'm getting back on track now."),
            ("rider", "I can see the GPS. I want a refund or I'll report this."),
        ]
    if label == "legit_detour":
        return [
            ("driver", "There's an accident ahead, the road is closed."),
            ("rider", "Okay, can you take another way?"),
            ("driver", "Yes, I'll detour around it. Traffic is heavy."),
            ("rider", "Thanks for letting me know."),
            ("driver", "We're past it now, ETA 5 minutes."),
        ]
    if label == "driver_no_show":
        return [
            ("rider", "I'm at the pickup point. Where are you?"),
            ("driver", "Almost there."),
            ("rider", "It's been 10 minutes and you haven't moved."),
            ("rider", "I'm being charged a cancellation fee for nothing!"),
            ("rider", "I'll report you and dispute this charge."),
        ]
    if label == "rider_no_show":
        return [
            ("driver", "I've arrived at your pickup location."),
            ("rider", "Give me 2 minutes."),
            ("driver", "I'm waiting right outside."),
            ("driver", "It's been over 5 minutes. Are you coming?"),
            ("rider", "Almost there."),
            ("driver", "I have to cancel the trip now, sorry."),
        ]
    if label == "surge_mismatch":
        return [
            ("rider", f"The fare is {actual:.2f} but my estimate was {est:.2f}."),
            ("driver", "That's surge pricing."),
            ("rider", "There was no surge when I booked."),
            ("rider", "I'll dispute this charge if it isn't corrected."),
        ]
    if label == "frivolous":
        return [
            ("rider", "You took the long way on purpose."),
            ("driver", "I followed the app's route."),
            ("rider", "I demand a full refund or I'll rate you one star and report you."),
            ("rider", "I know people at the company, you'll get fired."),
        ]
    if label == "repeated_deviation":
        return [
            ("rider", "You're going off route again."),
            ("driver", "Sorry, rerouting now."),
            ("rider", "This keeps happening with you."),
            ("driver", "I'll fix it."),
            ("rider", "I want a refund for the extra distance."),
        ]
    return [
        ("rider", "Thanks for coming."),
        ("driver", "We should arrive soon."),
        ("rider", "Please take the quickest route."),
        ("driver", "Sure, we're on the way."),
    ]


def outcome_refund(label, actual_fare, est_fare):
    if label in ("route_deviation", "driver_no_show", "repeated_deviation"):
        return "refund", round(actual_fare, 2)
    if label == "surge_mismatch":
        return "partial_refund", round(actual_fare - est_fare, 2)
    return "no_action", 0.0


async def build_trip(session, group, label, rider, driver, t_idx):
    pickup, dropoff = random_endpoints(RNG)
    optimal = make_optimal_route(pickup, dropoff, RNG)
    dist_km = route_length(optimal)
    dur_min = round(dist_km / 24.0 * 60.0, 1)
    est_fare = round(BASE_FARE + PER_KM_RATE * dist_km + PER_MIN_RATE * dur_min, 2)

    surge = 1.0
    cancel_fee = 0.0
    status = "completed"
    requested_at = BASE_TIME + dt.timedelta(hours=t_idx * 5, minutes=RNG.randrange(0, 120))

    if label in ("normal", "surge_mismatch", "frivolous"):
        wps = normal_waypoints(optimal, RNG)
        speeds = [RNG.uniform(24, 32) for _ in range(len(wps) - 1)]
    elif label in ("route_deviation", "repeated_deviation"):
        wps = deviation_waypoints(optimal, RNG)
        speeds = [RNG.uniform(26, 34) for _ in range(len(wps) - 1)]
    elif label == "legit_detour":
        wps, speeds = legit_detour_route(optimal, RNG)
    else:
        wps, speeds = [], []

    if label in ("driver_no_show", "rider_no_show"):
        cancel_fee = CANCELLATION_FEE
        status = "cancelled"
        if label == "driver_no_show":
            gps = driver_no_show_gps(pickup, requested_at + dt.timedelta(seconds=60), RNG)
            pickup_at = None
            dropoff_at = None
        else:
            gps, arrival = rider_no_show_gps(pickup, requested_at + dt.timedelta(seconds=60), RNG)
            pickup_at = arrival
            dropoff_at = None
    else:
        if label == "surge_mismatch":
            surge = round(RNG.uniform(2.0, 3.0), 1)
        gps, dur_s = simulate_drive(wps, speeds, 20.0, requested_at + dt.timedelta(seconds=60), RNG)
        pickup_at = requested_at + dt.timedelta(seconds=60)
        dropoff_at = pickup_at + dt.timedelta(seconds=dur_s)

    if label in ("driver_no_show", "rider_no_show"):
        actual_fare = cancel_fee
    else:
        actual_fare = round(est_fare * surge, 2)

    trip = models.Trip(
        rider_id=rider.id,
        driver_id=driver.id,
        requested_at=requested_at,
        pickup_at=pickup_at,
        dropoff_at=dropoff_at,
        estimated_fare=est_fare,
        actual_fare=actual_fare,
        surge_multiplier=surge,
        promo_code=None,
        promo_discount=0.0,
        base_fare=BASE_FARE,
        per_km_rate=PER_KM_RATE,
        per_min_rate=PER_MIN_RATE,
        cancellation_fee=cancel_fee,
        status=status,
        estimated_distance_km=round(dist_km, 2),
        estimated_duration_min=dur_min,
        optimal_route_polyline=[[round(p[0], 6), round(p[1], 6)] for p in optimal],
    )
    session.add(trip)
    await session.flush()

    for lat, lng, ts, spd in gps:
        session.add(
            models.GpsPoint(
                trip_id=trip.id, lat=round(lat, 6), lng=round(lng, 6), ts=ts, speed_kmh=spd
            )
        )

    messages = chat_for(label, rider.name, driver.name, est_fare, actual_fare)
    for idx, (speaker, text) in enumerate(messages):
        sender_id = rider.id if speaker == "rider" else driver.id
        session.add(
            models.ChatMessage(
                trip_id=trip.id,
                sender_id=sender_id,
                text=text,
                ts=requested_at + dt.timedelta(seconds=(idx + 1) * 90),
            )
        )

    if label == "normal":
        return None

    dispute = models.Dispute(
        trip_id=trip.id,
        filed_by=rider.id,
        category=CATEGORY[label],
        claim_text=CLAIM_TEXT[label],
        status="open",
        priority=PRIORITY[label],
        created_at=requested_at + dt.timedelta(hours=1),
    )
    session.add(dispute)
    await session.flush()

    outcome, refund = outcome_refund(label, actual_fare, est_fare)
    return {
        "trip_id": trip.id,
        "dispute_id": dispute.id,
        "scenario": group,
        "label": label,
        "category": dispute.category.value,
        "rider_id": rider.id,
        "driver_id": driver.id,
        "expected_outcome": outcome,
        "expected_refund_amount": refund,
    }


async def main():
    async with async_session_factory() as session:
        await session.execute(
            text(
                "TRUNCATE TABLE accounts, trips, gps_points, chat_messages, disputes, "
                "rulings, agent_messages, policy_chunks RESTART IDENTITY CASCADE"
            )
        )
        await session.commit()

        riders = []
        drivers = []
        for i in range(10):
            rider = models.Account(
                role=AccountRole.rider,
                name=RIDER_NAMES[i],
                rating=RIDER_RATINGS[i],
                age_band=RIDER_AGE_BANDS[i],
                created_at=BASE_TIME,
            )
            session.add(rider)
            riders.append(rider)
        for i in range(10):
            driver = models.Account(
                role=AccountRole.driver,
                name=DRIVER_NAMES[i],
                rating=DRIVER_RATINGS[i],
                age_band=DRIVER_AGE_BANDS[i],
                created_at=BASE_TIME,
            )
            session.add(driver)
            drivers.append(driver)
        await session.flush()

        ground_truth = []
        t_idx = 0

        for group, label, r_idx, d_idx in SPECS:
            t_idx += 1
            entry = await build_trip(session, group, label, riders[r_idx], drivers[d_idx], t_idx)
            if entry is not None:
                ground_truth.append(entry)

        for _ in range(14):
            t_idx += 1
            await build_trip(
                session, "normal", "normal", riders[RNG.randrange(10)], drivers[RNG.randrange(10)], t_idx
            )

        await session.commit()

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out_path = DATA_DIR / "ground_truth.json"
    out_path.write_text(json.dumps(ground_truth, indent=2), encoding="utf-8")
    print(f"Seeded {t_idx} trips and {len(ground_truth)} disputes -> {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
