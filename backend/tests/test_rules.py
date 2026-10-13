from types import SimpleNamespace

import pytest

from app.evidence import route as route_evidence
from app.rules import Rule, evaluate, load_rules
from app.rules.evaluator import safe_eval
from tests.conftest import trip_id_for


def _item(data):
    return SimpleNamespace(data=data)


def test_safe_eval_arithmetic():
    assert safe_eval("1 + 2 * 3", {}) == 7
    assert safe_eval("x / 2", {"x": 10}) == 5.0


def test_safe_eval_boolean_comparison():
    ctx = {"a": 3, "b": 1, "flag": True}
    assert safe_eval("a > 2 and not (b > 1)", ctx) is True
    assert safe_eval("a > 2 and b > 1", ctx) is False
    assert safe_eval("flag or a < 0", ctx) is True


def test_safe_eval_functions():
    assert safe_eval("min(1, x / 10)", {"x": 5}) == 0.5
    assert safe_eval("abs(-3)", {}) == 3


def test_safe_eval_rejects_dangerous():
    with pytest.raises(ValueError):
        safe_eval("__import__('os')", {})
    with pytest.raises(ValueError):
        safe_eval("x.__class__", {"x": 1})
    with pytest.raises(ValueError):
        safe_eval("eval('1+1')", {})


def test_evaluate_route_deviation_partial_refund():
    rules = [
        Rule(
            id="r1",
            category="route_deviation",
            conditions="extra_distance_km > 2 and not traffic_signal",
            outcome="partial_refund",
            amount="fare * min(1, extra_distance_km / total_km)",
        )
    ]
    evidence = [_item({"extra_distance_km": 4.0, "traffic_signal": False, "fare": 20.0, "total_km": 8.0})]
    result = evaluate("route_deviation", evidence, rules=rules)
    assert result.outcome == "partial_refund"
    assert result.refund_amount == 10.0
    assert result.matched_rule_ids == ["r1"]


def test_evaluate_no_show_full_refund_fee():
    rules = [
        Rule(id="ns1", category="no_show", conditions="not driver_arrived", outcome="full_refund", amount="fee")
    ]
    result = evaluate("no_show", [_item({"driver_arrived": False, "fee": 6.0})], rules=rules)
    assert result.outcome == "full_refund"
    assert result.refund_amount == 6.0


def test_evaluate_fare_discrepancy():
    rules = [
        Rule(
            id="f1",
            category="fare",
            conditions="abs(arithmetic_discrepancy) > 0.05 * recomputed_expected_fare",
            outcome="partial_refund",
            amount="abs(arithmetic_discrepancy)",
        )
    ]
    evidence = [_item({"arithmetic_discrepancy": 3.0, "recomputed_expected_fare": 10.0})]
    result = evaluate("fare", evidence, rules=rules)
    assert result.outcome == "partial_refund"
    assert result.refund_amount == 3.0


def test_evaluate_no_match_defaults_to_no_action():
    rules = [
        Rule(id="r1", category="route_deviation", conditions="extra_distance_km > 2", outcome="partial_refund", amount="1")
    ]
    result = evaluate("route_deviation", [_item({"extra_distance_km": 0.2})], rules=rules)
    assert result.outcome == "no_action"
    assert result.refund_amount == 0.0
    assert result.matched_rule_ids == []


def test_evaluate_rounds_to_2_decimals():
    rules = [Rule(id="r1", category="c", conditions="x > 0", outcome="partial_refund", amount="x / 3")]
    result = evaluate("c", [_item({"x": 10.0})], rules=rules)
    assert result.refund_amount == 3.33


def test_load_rules_real_yaml():
    rules = load_rules()
    categories = {r.category for r in rules}
    assert {"route_deviation", "no_show", "fare_dispute"} <= categories
    assert all(r.id and r.conditions for r in rules)


async def test_scenario_A_rules_partial_refund(seeded_session, ground_truth):
    tid = trip_id_for(ground_truth, "route_deviation")
    evidence = await route_evidence.analyze_route_deviation(tid, session=seeded_session)
    result = evaluate("route_deviation", [evidence])
    assert result.outcome == "partial_refund"
    assert result.refund_amount > 0
    assert result.matched_rule_ids == ["route_deviation_major"]
