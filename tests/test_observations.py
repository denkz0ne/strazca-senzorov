from datetime import UTC, datetime, timedelta

from custom_components.sensor_guardian.history import (
    prune_battery_history,
    record_health,
    record_signal,
)
from custom_components.sensor_guardian.models import empty_store_data


def test_same_state_checks_do_not_make_fake_health_transitions():
    data = empty_store_data()
    device = {"device_id": "a", "health_state": "healthy", "health_reason": "available"}
    now = datetime(2026, 10, 7, tzinfo=UTC)
    assert record_health(data, device, now=now)
    assert not record_health(data, device, now=now + timedelta(minutes=1))
    device["health_state"] = "offline"
    assert record_health(data, device, now=now + timedelta(minutes=2))
    assert len(data["health_history"]) == 2


def test_signal_changes_and_checkpoints_are_retained_but_duplicates_are_not():
    data = empty_store_data()
    now = datetime(2026, 10, 7, tzinfo=UTC)
    assert record_signal(data, "a", "rssi", -65, now=now)
    assert not record_signal(data, "a", "rssi", -65, now=now + timedelta(seconds=30))
    assert record_signal(data, "a", "rssi", -80, now=now + timedelta(minutes=2))
    assert record_signal(data, "a", "rssi", -80, now=now + timedelta(hours=2))
    assert len(data["signal_samples"]) == 3


def test_battery_retention_is_per_device_and_preserves_last_known_value():
    data = empty_store_data()
    now = datetime(2026, 10, 7, tzinfo=UTC)
    data["settings"]["retention_days"] = 30
    data["samples"] = [
        {
            "sample_id": "old",
            "device_id": "quiet",
            "timestamp": (now - timedelta(days=60)).isoformat(),
            "level_percent": 50,
        }
    ]
    data["samples"] += [
        {
            "sample_id": str(i),
            "device_id": "chatty",
            "timestamp": (now - timedelta(seconds=5000 - i)).isoformat(),
            "level_percent": 80,
        }
        for i in range(5000)
    ]
    assert prune_battery_history(data, now=now)
    assert any(row["device_id"] == "quiet" for row in data["samples"])
    assert len([row for row in data["samples"] if row["device_id"] == "chatty"]) == 4096
