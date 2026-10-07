from datetime import UTC, datetime, timedelta

from custom_components.sensor_guardian.history import record_health, record_signal

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
