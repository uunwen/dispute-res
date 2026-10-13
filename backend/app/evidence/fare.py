from sqlalchemy import select

from app.db import models
from app.db.session import async_session_factory
from app.evidence.base import result_to_evidence
from app.schemas.evidence import EvidenceItem

_EPSILON = 0.011


def compute_fare(trip):
    """Recompute the expected fare and compare it against what was charged.

    ``trip`` is any object exposing ``base_fare``, ``per_km_rate``,
    ``per_min_rate``, ``estimated_distance_km``, ``estimated_duration_min``,
    ``surge_multiplier``, ``promo_discount``, ``estimated_fare`` and
    ``actual_fare``. The computation is pure arithmetic.
    """
    base = trip.base_fare
    dist = trip.estimated_distance_km
    dur = trip.estimated_duration_min
    surge = trip.surge_multiplier
    promo = trip.promo_discount or 0.0
    estimated = trip.estimated_fare
    actual = trip.actual_fare

    recomputed_base = base + trip.per_km_rate * dist + trip.per_min_rate * dur
    recomputed_expected = recomputed_base * surge - promo
    discrepancy = actual - recomputed_expected
    surge_premium = recomputed_base * (surge - 1.0)
    quote_discrepancy = actual - estimated

    if abs(discrepancy) > _EPSILON:
        cause = "fare_miscalculation"
    elif surge > 1.0 + 1e-6:
        cause = "surge_applied"
    elif promo > 0:
        cause = "promo_applied"
    else:
        cause = "none"

    data = {
        "recomputed_base_fare": round(recomputed_base, 2),
        "recomputed_expected_fare": round(recomputed_expected, 2),
        "arithmetic_discrepancy": round(discrepancy, 2),
        "surge_multiplier": surge,
        "surge_premium": round(surge_premium, 2),
        "promo_discount": round(promo, 2),
        "quote_discrepancy": round(quote_discrepancy, 2),
        "likely_cause": cause,
    }

    if cause == "surge_applied":
        supports = "rider"
        strength = min(1.0, max(0.3, (surge - 1.0)))
        summary = (
            f"Surge multiplier {surge}x applied ({surge_premium:.2f} premium over base fare)."
        )
    elif cause == "fare_miscalculation":
        supports = "rider" if discrepancy > 0 else "driver"
        strength = min(1.0, abs(discrepancy) / 10.0 + 0.3)
        summary = f"Fare does not match pricing formula (discrepancy {discrepancy:+.2f})."
    elif cause == "promo_applied":
        supports = "neutral"
        strength = 0.2
        summary = f"Promo discount of {promo:.2f} applied to the fare."
    else:
        supports = "neutral"
        strength = 0.15
        summary = "Fare is consistent with the pricing formula."

    return {"supports": supports, "strength": strength, "summary": summary, "data": data}


async def validate_fare(trip_id: int, session=None) -> EvidenceItem:
    async def _run(s):
        trip = (
            await s.execute(select(models.Trip).where(models.Trip.id == trip_id))
        ).scalar_one_or_none()
        if trip is None:
            raise ValueError(f"trip {trip_id} not found")
        result = compute_fare(trip)
        return result_to_evidence("fare_validation", trip_id, trip_id, result)

    if session is not None:
        return await _run(session)
    async with async_session_factory() as s:
        return await _run(s)
