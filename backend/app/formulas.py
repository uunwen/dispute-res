"""Single source of truth for the deterministic calculations used by the system.

Every number the system produces is computed by plain Python (the LLM never does
math). This module documents each formula alongside its source location so the
OpenAPI/Swagger description and the ``GET /meta/formulas`` endpoint stay in sync
with the code.
"""

from pydantic import BaseModel, Field


class FormulaVariable(BaseModel):
    name: str
    definition: str


class Formula(BaseModel):
    id: str
    name: str
    category: str
    formula: str
    description: str
    variables: list[FormulaVariable] = Field(default_factory=list)
    source: str


FORMULAS: list[Formula] = [
    Formula(
        id="confidence_score",
        name="Judge confidence score",
        category="Ruling",
        formula="confidence = 0.35\u00b7agreement + 0.30\u00b7evidence_strength + 0.20\u00b7citation_validity + 0.15\u00b7history_risk",
        description=(
            "Documented confidence formula (not LLM self-reported). All components "
            "are in [0, 1]. The result is clamped to [0, 1] and a fraud penalty is "
            "then subtracted (see fraud_penalty)."
        ),
        variables=[
            FormulaVariable(
                name="agreement",
                definition="1.0 when the LLM and the rules engine agree on the outcome, otherwise 0.3.",
            ),
            FormulaVariable(
                name="evidence_strength",
                definition="Mean strength of the cited deciding evidence items.",
            ),
            FormulaVariable(
                name="citation_validity",
                definition="Fraction of the LLM's cited evidence ids that actually exist.",
            ),
            FormulaVariable(
                name="history_risk",
                definition="Maximum abuse-risk score across the rider and driver.",
            ),
        ],
        source="app/agents/judge.py:compute_confidence",
    ),
    Formula(
        id="rule_llm_reconcile",
        name="Rule / LLM refund reconciliation",
        category="Ruling",
        formula="final_amount = min(rule_amount, max(llm_amount, 0.0))",
        description=(
            "The rules engine is the source of truth for the amount. The LLM may "
            "reduce the refund but never exceed the rule amount. The final outcome "
            "is derived from the final amount."
        ),
        variables=[
            FormulaVariable(name="rule_amount", definition="Refund amount from the deterministic rules engine."),
            FormulaVariable(name="llm_amount", definition="Refund amount proposed by the Judge LLM."),
        ],
        source="app/agents/judge.py:reconcile",
    ),
    Formula(
        id="fraud_penalty",
        name="Fraud confidence penalty",
        category="Ruling",
        formula="fraud_penalty = fraud_penalty_weight \u00b7 risk  (only when favored side's risk \u2265 threshold)",
        description=(
            "When the side being favored (rider for refunds, driver for no_action) "
            "has fraud risk at or above the threshold, confidence is reduced. The "
            "signal is advisory: it never changes the outcome. Defaults: "
            "weight = 0.2, threshold = 0.5."
        ),
        variables=[
            FormulaVariable(name="fraud_penalty_weight", definition="0.2 (configurable via settings)."),
            FormulaVariable(name="fraud_penalty_threshold", definition="0.5 (configurable via settings)."),
        ],
        source="app/agents/judge.py:_fraud_penalty",
    ),
    Formula(
        id="history_abuse_risk",
        name="Account abuse-risk profile",
        category="Evidence",
        formula="abuse_risk = 0.50\u00b7dispute_factor + 0.25\u00b7(1 - win_rate) + 0.25\u00b7rating_factor",
        description="Weighted combination of dispute frequency, loss rate and rating.",
        variables=[
            FormulaVariable(name="dispute_factor", definition="min(1, dispute_count / 8)."),
            FormulaVariable(name="win_rate", definition="won_count / resolved_count, or 0.5 when nothing is resolved."),
            FormulaVariable(name="rating_factor", definition="max(0, 1 - rating / 5)."),
        ],
        source="app/evidence/history.py:compute_history_profile",
    ),
    Formula(
        id="fare_recompute",
        name="Fare recomputation",
        category="Evidence",
        formula=(
            "recomputed_base = base_fare + per_km_rate\u00b7distance + per_min_rate\u00b7duration\n"
            "recomputed_expected = recomputed_base\u00b7surge_multiplier - promo_discount\n"
            "arithmetic_discrepancy = actual_fare - recomputed_expected"
        ),
        description=(
            "Pure arithmetic fare validation. A non-zero discrepancy beyond "
            "0.011 flags a fare miscalculation; otherwise surge/promo are identified."
        ),
        variables=[
            FormulaVariable(name="surge_premium", definition="recomputed_base \u00b7 (surge_multiplier - 1)."),
            FormulaVariable(name="quote_discrepancy", definition="actual_fare - estimated_fare."),
        ],
        source="app/evidence/fare.py:compute_fare",
    ),
    Formula(
        id="route_deviation",
        name="Route deviation detection",
        category="Evidence",
        formula=(
            "fraction_outside = outside_buffer_points / total_points\n"
            "extra_distance = actual_distance - optimal_distance\n"
            "bad_faith = fraction_outside \u2265 min_fraction AND extra_distance \u2265 min_extra_km AND not traffic_signal"
        ),
        description=(
            "GPS fixes are projected to EPSG:3414 (SVY21, metres) with pyproj and "
            "classified inside/outside a buffer around the optimal route. Distance "
            "uses the haversine formula. A slow-speed stretch immediately before "
            "leaving the route is treated as a legitimate traffic detour."
        ),
        variables=[
            FormulaVariable(name="haversine_km", definition="Great-circle distance between two lat/lng points."),
            FormulaVariable(name="traffic_signal", definition="avg speed on-route before deviation < traffic_speed_kmh (15 km/h)."),
        ],
        source="app/evidence/route.py:compute_route_deviation",
    ),
    Formula(
        id="noshow_detection",
        name="No-show classification",
        category="Evidence",
        formula=(
            "driver_arrived = min_distance_to_pickup \u2264 proximity_m\n"
            "cancellation_fee_valid = driver_arrived AND wait_duration \u2265 min_wait_min"
        ),
        description=(
            "A no-show is classified from GPS distance to the pickup point and the "
            "duration the driver stayed within the proximity threshold."
        ),
        variables=[
            FormulaVariable(name="proximity_m", definition="100 m (configurable)."),
            FormulaVariable(name="min_wait_min", definition="5 min (configurable)."),
        ],
        source="app/evidence/noshow.py:compute_noshow",
    ),
    Formula(
        id="fraud_risk",
        name="Fraud risk scoring",
        category="Fraud",
        formula="risk = \u03a3 fired_rule_weight, clamped to [0, 1]",
        description=(
            "Rule-based (no LLM) advisory scoring. Fired rules add their weight to "
            "the relevant side's risk."
        ),
        variables=[
            FormulaVariable(name="dispute_frequency", definition="weight 0.3 \u2014 \u2265 threshold disputes within N days."),
            FormulaVariable(name="win_rate_anomaly", definition="weight 0.2 \u2014 win rate below threshold."),
            FormulaVariable(name="repeat_deviation", definition="weight 0.4 \u2014 driver in \u2265 threshold route-deviation disputes."),
            FormulaVariable(name="young_account", definition="weight 0.2 \u2014 account age below N days."),
            FormulaVariable(name="claim_evidence_contradiction", definition="weight 0.3 \u2014 claim contradicted by deterministic evidence."),
        ],
        source="app/agents/fraud.py:_WEIGHTS",
    ),
    Formula(
        id="queue_priority",
        name="Queue priority (SLA & routing)",
        category="Queue",
        formula="priority = safety\u00b71e15 + amount\u00b71e8 + age_seconds\u00b71.0",
        description=(
            "Redis sorted-set score. Weights are chosen so safety > amount > age "
            "for realistic fares and ages. Safety incidents are always fast-tracked."
        ),
        variables=[
            FormulaVariable(name="safety", definition="1 if category is safety_incident, else 0."),
            FormulaVariable(name="amount", definition="The trip's disputed amount (actual fare)."),
            FormulaVariable(name="age_seconds", definition="Seconds since the dispute was filed."),
        ],
        source="app/queue/queue.py:priority_score",
    ),
    Formula(
        id="chat_sentiment",
        name="Chat sentiment (VADER)",
        category="Evidence",
        formula="compound = mean(VADER compound score per message)",
        description=(
            "Deterministic average of per-message VADER sentiment. Optional LLM "
            "extraction adds threats, admissions, agreements, disagreements and "
            "key claims with message-id citations."
        ),
        variables=[],
        source="app/evidence/chat.py:vader_sentiment",
    ),
]


def formulas_markdown() -> str:
    lines = ["## Deterministic formulas", ""]
    for f in FORMULAS:
        lines.append(f"### {f.name}  (`{f.id}`)")
        lines.append("")
        lines.append(f"```\n{f.formula}\n```")
        lines.append("")
        lines.append(f.description)
        lines.append("")
        if f.variables:
            lines.append("| Variable | Definition |")
            lines.append("| --- | --- |")
            for v in f.variables:
                lines.append(f"| `{v.name}` | {v.definition} |")
            lines.append("")
        lines.append(f"_Source: `{f.source}`_")
        lines.append("")
    return "\n".join(lines).strip()
