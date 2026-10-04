from custom_components.sensor_guardian.diagnosis.scoring import (
    classify_cause,
    score_evidence,
)


def test_labeled_battery_and_gateway_evidence_explains_selected_causes():
    battery = score_evidence(
        [
            {"feature": "battery_level", "value": 3},
            {"feature": "native_battery_low", "value": True},
        ]
    )
    assert classify_cause(battery)["cause"] == "battery"
    assert battery["score_semantics"] == "evidence_points_not_probability"
    assert battery["ranked_causes"][0]["reasons"]

    gateway = score_evidence(
        [
            {"feature": "coordinator_unavailable", "value": True},
            {"feature": "shared_outage_count", "value": 5},
        ]
    )
    assert classify_cause(gateway)["cause"] == "gateway_upstream"

    rf_dropout = score_evidence(
        [
            {"feature": "single_device_dropout", "value": True},
            {"feature": "signal_trend", "value": "degrading"},
            {"feature": "rssi_dbm", "value": -95},
            {"feature": "recovered_without_battery_change", "value": True},
        ]
    )
    assert classify_cause(rf_dropout)["cause"] == "connectivity"

    source_failure = score_evidence(
        [
            {"feature": "source_entry_unavailable", "value": True},
            {"feature": "source_entry_outage_count", "value": 4},
        ]
    )
    assert classify_cause(source_failure)["cause"] == "integration"


def test_weak_or_conflicting_evidence_stays_unknown():
    weak = classify_cause(score_evidence([{"feature": "rssi_dbm", "value": -92}]))
    assert weak["cause"] == "unknown"
    assert weak["reason_code"] == "score_below_threshold"

    conflict = classify_cause(
        score_evidence(
            [
                {"feature": "battery_level", "value": 3},
                {"feature": "native_battery_low", "value": True},
                {"feature": "coordinator_unavailable", "value": True},
                {"feature": "shared_outage_count", "value": 3},
            ]
        )
    )
    assert conflict["cause"] == "unknown"
    assert conflict["reason_code"] == "competing_evidence"


def test_stale_or_invalid_evidence_is_not_scored():
    result = score_evidence(
        [{"feature": "battery_level", "value": 0, "quality": "stale"}]
    )
    assert result["scores"]["battery"] == 0
