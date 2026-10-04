from datetime import UTC, datetime, timedelta

from custom_components.sensor_guardian.diagnosis.incidents import (
    close_incident,
    open_or_update_incident,
    revise_cause,
)
from custom_components.sensor_guardian.models import empty_store_data


def test_incident_deduplicates_and_keeps_cause_revision_audit():
    now = datetime(2025, 1, 1, tzinfo=UTC)
    data, incident = open_or_update_incident(
        empty_store_data(),
        device_ids=["d1"],
        now=now,
        health_state="offline",
        cause_result={
            "cause": "unknown",
            "confidence": "none",
            "reason_code": "no_evidence",
        },
        evidence=[{"feature": "last_reported", "value": "old"}],
    )
    same, again = open_or_update_incident(
        data,
        device_ids=["d1"],
        now=now + timedelta(minutes=1),
        health_state="offline",
        cause_result={
            "cause": "unknown",
            "confidence": "none",
            "reason_code": "no_evidence",
        },
        evidence=[{"feature": "battery_level", "value": 4}],
    )
    assert len(same["incidents"]) == 1
    assert again["incident_id"] == incident["incident_id"]
    revised, changed = revise_cause(
        again,
        {
            "cause": "battery",
            "confidence": "high",
            "reason_code": "score_and_margin_met",
        },
        [{"feature": "battery_level", "value": 3}],
        now=now + timedelta(minutes=2),
        provenance="user_confirmed",
    )
    assert changed is True
    assert revised["confirmed_cause"] == "battery"
    assert revised["cause_history"][-1]["previous_cause"] == "unknown"
    repeated, changed = revise_cause(
        revised,
        {"cause": "battery", "confidence": "high"},
        revised["evidence"],
        now=now + timedelta(minutes=3),
        provenance="user_confirmed",
    )
    assert changed is False
    assert len(repeated["cause_history"]) == 2


def test_incident_close_is_idempotent_and_retains_history():
    now = datetime(2025, 1, 1, tzinfo=UTC)
    _, incident = open_or_update_incident(
        empty_store_data(),
        device_ids=["d1", "d2"],
        now=now,
        health_state="offline",
        cause_result={"cause": "gateway_upstream", "confidence": "medium"},
        evidence=[],
        dependency_id="dep-a",
    )
    closed = close_incident(incident, now=now + timedelta(hours=1))
    assert close_incident(closed, now=now + timedelta(hours=2)) == closed
    assert closed["dependency_id"] == "dep-a"
    assert closed["notification_state"] == "recovered"
