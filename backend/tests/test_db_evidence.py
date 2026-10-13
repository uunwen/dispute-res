import pytest

from app.config import settings
from app.evidence import chat, fare, history, noshow, route
from tests.conftest import trip_id_for

SERIAL_ABUSER_RIDER_ID = 10
NORMAL_RIDER_ID = 1


async def test_scenario_A_flags_deviation(seeded_session, ground_truth):
    tid = trip_id_for(ground_truth, "route_deviation")
    evidence = await route.analyze_route_deviation(tid, session=seeded_session)
    assert evidence.data["bad_faith_deviation"] is True
    assert evidence.data["extra_distance_km"] >= 2.0
    assert evidence.supports == "rider"


async def test_scenario_B_not_bad_faith(seeded_session, ground_truth):
    tid = trip_id_for(ground_truth, "legit_detour")
    evidence = await route.analyze_route_deviation(tid, session=seeded_session)
    assert evidence.data["bad_faith_deviation"] is False


async def test_scenario_C_driver_no_show(seeded_session, ground_truth):
    tid = trip_id_for(ground_truth, "driver_no_show")
    evidence = await noshow.analyze_noshow(tid, session=seeded_session)
    assert evidence.data["driver_arrived"] is False
    assert evidence.data["cancellation_fee_valid"] is False
    assert evidence.supports == "rider"


async def test_scenario_D_rider_no_show(seeded_session, ground_truth):
    tid = trip_id_for(ground_truth, "rider_no_show")
    evidence = await noshow.analyze_noshow(tid, session=seeded_session)
    assert evidence.data["driver_arrived"] is True
    assert evidence.data["wait_duration_min"] >= 5.0
    assert evidence.data["cancellation_fee_valid"] is True
    assert evidence.supports == "driver"


async def test_completed_trip_not_no_show(seeded_session, ground_truth):
    trip_id = next(e["trip_id"] for e in ground_truth if e["label"] == "repeated_deviation")
    evidence = await noshow.analyze_noshow(trip_id, session=seeded_session)
    assert evidence.data["driver_arrived"] is True
    assert evidence.data["cancellation_fee_valid"] is False
    assert evidence.supports == "neutral"


async def test_scenario_E_surge_mismatch(seeded_session, ground_truth):
    tid = trip_id_for(ground_truth, "surge_mismatch")
    evidence = await fare.validate_fare(tid, session=seeded_session)
    assert evidence.data["likely_cause"] == "surge_applied"
    assert evidence.data["surge_multiplier"] > 1.0
    assert evidence.supports == "rider"


async def test_history_serial_abuser(seeded_session):
    abuser = await history.compute_history_profile_db(SERIAL_ABUSER_RIDER_ID, session=seeded_session)
    normal = await history.compute_history_profile_db(NORMAL_RIDER_ID, session=seeded_session)
    assert abuser.data["dispute_count"] == 8
    assert normal.data["dispute_count"] <= 2
    assert abuser.data["dispute_count"] > normal.data["dispute_count"]
    assert abuser.data["abuse_risk_score"] > normal.data["abuse_risk_score"]
    assert abuser.data["abuse_risk_score"] > settings.abuse_risk_threshold


async def test_chat_analysis_runs(seeded_session, ground_truth):
    tid = trip_id_for(ground_truth, "frivolous")
    chat.clear_cache()
    evidence = await chat.analyze_chat(tid, session=seeded_session)
    assert evidence.type == "chat_analysis"
    assert evidence.data["message_count"] >= 3
