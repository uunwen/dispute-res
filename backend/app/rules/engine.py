from pathlib import Path

import yaml

from app.rules.evaluator import safe_eval
from app.rules.models import Rule, RuleResult

_DEFAULT_RULES_PATH = Path(__file__).resolve().parents[2] / "rules" / "rules.yaml"

_cache: list[Rule] | None = None


def load_rules(path=None) -> list[Rule]:
    """Load rules from YAML (defaults to ``rules/rules.yaml``)."""
    global _cache
    target = Path(path) if path else _DEFAULT_RULES_PATH
    data = yaml.safe_load(target.read_text(encoding="utf-8"))
    rules = [Rule(**r) for r in data["rules"]]
    if path is None:
        _cache = rules
    return rules


def build_context(evidence_items) -> dict:
    """Flatten every evidence item's ``data`` dict into a single context.

    Rules reference these fields by name (e.g. ``extra_distance_km``,
    ``traffic_signal``, ``driver_arrived``, ``fee``, ``fare``, ``total_km``).
    """
    ctx: dict = {}
    for item in evidence_items:
        ctx.update(item.data)
    return ctx


def evaluate(category: str, evidence_items, rules=None) -> RuleResult:
    """Evaluate rules for ``category`` against the evidence and return a RuleResult.

    Rules are evaluated in YAML order; the first matching rule wins and
    determines the outcome and refund amount. Money is rounded to 2 decimals.
    """
    if rules is None:
        rules = _cache if _cache is not None else load_rules()

    ctx = build_context(evidence_items)

    # EXTENSION POINT: to add more deterministic rules, append entries to
    # rules/rules.yaml (see the file header). No code change is required here as
    # long as the referenced fields exist in the evidence data dicts. The
    # conditions/amount expressions are evaluated by the safe evaluator and are
    # never passed to eval().
    for rule in rules:
        if rule.category != category:
            continue
        if safe_eval(rule.conditions, ctx):
            refund = round(float(safe_eval(rule.amount, ctx)), 2)
            return RuleResult(
                outcome=rule.outcome,
                refund_amount=refund,
                matched_rule_ids=[rule.id],
                explanation=f"Matched rule '{rule.id}': {rule.conditions}",
            )

    return RuleResult(
        outcome="no_action",
        refund_amount=0.0,
        matched_rule_ids=[],
        explanation=f"No rule in category '{category}' matched.",
    )
