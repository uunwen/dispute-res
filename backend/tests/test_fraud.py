from app.agents.fraud import analyze_fraud, compute_fraud_signal
from app.agents.judge import Judge
from app.schemas.fraud import FraudSignal


def _facts(**overrides):
    defaults = {
        "trip_id": 1,
        "rider_disputes": 0,
        "driver_disputes": 0,
        "rider_win_rate": 0.5,
        "driver_win_rate": 0.5,
        "driver_deviation_count": 0,
        "rider_account_age_days": 100,
        "driver_account_age_days": 100,
        "contradiction": False,
        "contradiction_evidence_id": "",
        "rider_history_id": "history_profile:1",
        "driver_history_id": "history_profile:11",
        "dispute_frequency_days": 30,
        "dispute_frequency_threshold": 3,
        "win_rate_threshold": 0.4,
        "repeat_deviation_threshold": 2,
        "account_age_days": 14,
    }
    defaults.update(overrides)
    return defaults


def test_compute_fraud_signal_dispute_frequency():
    signal = compute_fraud_signal(_facts(rider_disputes=8))
    assert signal.rider_risk > 0
    assert signal.driver_risk == 0.0
    assert any(r.code == "dispute_frequency" for r in signal.reasons)


def test_compute_fraud_signal_repeat_deviation():
    signal = compute_fraud_signal(_facts(driver_deviation_count=3))
    assert signal.driver_risk > 0
    assert signal.rider_risk == 0.0
    assert any(r.code == "repeat_deviation" for r in signal.reasons)


def test_compute_fraud_signal_contradiction():
    signal = compute_fraud_signal(
        _facts(contradiction=True, contradiction_evidence_id="route_deviation:1")
    )
    assert signal.rider_risk > 0
    assert any(r.code == "claim_evidence_contradiction" for r in signal.reasons)


def test_fraud_penalty_applies_to_favored_side():
    judge = Judge()
    signal = FraudSignal(trip_id=1, rider_risk=0.8, driver_risk=0.0, reasons=[])
    assert judge._fraud_penalty("partial_refund", signal) > 0
    assert judge._fraud_penalty("no_action", signal) == 0.0


def test_fraud_penalty_zero_when_risk_low():
    judge = Judge()
    signal = FraudSignal(trip_id=1, rider_risk=0.2, driver_risk=0.0, reasons=[])
    assert judge._fraud_penalty("partial_refund", signal) == 0.0


async def test_analyze_fraud_serial_abuser(seeded_session, ground_truth):
    trip_id = next(e["trip_id"] for e in ground_truth if e["label"] == "frivolous")
    signal = await analyze_fraud(trip_id)
    assert signal.rider_risk >= 0.5
    assert any(r.code == "dispute_frequency" for r in signal.reasons)


async def test_analyze_fraud_repeat_deviation_driver(seeded_session, ground_truth):
    trip_id = next(e["trip_id"] for e in ground_truth if e["label"] == "repeated_deviation")
    signal = await analyze_fraud(trip_id)
    assert signal.driver_risk >= 0.4
    assert any(r.code == "repeat_deviation" for r in signal.reasons)
