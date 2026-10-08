from datetime import UTC, datetime

from custom_components.sensor_guardian.diagnosis.incidents import (
    open_or_update_incident,
    sync_battery_alert,
)
from custom_components.sensor_guardian.models import empty_store_data


def test_battery_warning_and_availability_incident_have_independent_lifecycles():
    data = empty_store_data()
    device = {
        "device_id": "a",
        "battery_attention": True,
        "tracking_mode": "battery_only",
        "power_type": "replaceable_battery",
    }
    data["devices"].append(device)
    now = datetime.now(UTC)
    sync_battery_alert(data, device, now=now, level=15, native_low=False, estimate={})
    updated, outage = open_or_update_incident(
        data,
        device_ids=["a"],
        now=now,
        health_state="offline",
        cause_result={"cause": "unknown", "confidence": "none"},
        evidence=[],
    )
    assert len(updated["incidents"]) == 2
    assert outage.get("kind", "availability") == "availability"
    device["battery_attention"] = False
    sync_battery_alert(
        updated, device, now=now, level=90, native_low=False, estimate={}
    )
    battery = next(row for row in updated["incidents"] if row.get("kind") == "battery")
    assert battery["closed_at"]
    assert not next(
        row
        for row in updated["incidents"]
        if row["incident_id"] == outage["incident_id"]
    ).get("closed_at")
