from datetime import UTC, datetime

from custom_components.sensor_guardian.diagnosis.incidents import revise_cause


def test_explicit_cause_confirmation_survives_periodic_unknown_inference():
    incident = {
        "incident_id": "i",
        "device_ids": ["a"],
        "cause": "connectivity",
        "confidence": "high",
        "confirmed_cause": "connectivity",
        "cause_history": [],
    }
    revised, changed = revise_cause(
        incident,
        {"cause": "unknown", "confidence": "none"},
        [],
        now=datetime.now(UTC),
        provenance="inferred",
    )
    assert not changed
    assert revised["cause"] == "connectivity"
    assert revised["confidence"] == "high"
