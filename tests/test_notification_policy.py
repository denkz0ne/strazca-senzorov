from datetime import UTC, datetime

from custom_components.sensor_guardian.notification_policy import allowed


def test_quiet_hours_cross_midnight_but_critical_device_is_explicit_exception():
    data = {
        "settings": {
            "notifications_enabled": True,
            "quiet_start": "22:00",
            "quiet_end": "06:00",
        }
    }
    device = {"device_id": "a"}
    assert not allowed(
        data, device, now=datetime(2026, 10, 7, 23, tzinfo=UTC), time_zone="UTC"
    )
    assert not allowed(
        data, device, now=datetime(2026, 10, 8, 3, tzinfo=UTC), time_zone="UTC"
    )
    assert allowed(
        data, device, now=datetime(2026, 10, 8, 9, tzinfo=UTC), time_zone="UTC"
    )
    device["rules"] = {"criticality": "critical"}
    assert allowed(
        data, device, now=datetime(2026, 10, 7, 23, tzinfo=UTC), time_zone="UTC"
    )


def test_snooze_and_global_disable_are_not_overridden_by_criticality():
    now = datetime(2026, 10, 7, 23, tzinfo=UTC)
    device = {"device_id": "a", "rules": {"criticality": "critical"}}
    assert not allowed({"settings": {"notifications_enabled": False}}, device, now=now)
    device["snoozed_until"] = "2026-10-08T00:00:00+00:00"
    assert not allowed({"settings": {}}, device, now=now)
