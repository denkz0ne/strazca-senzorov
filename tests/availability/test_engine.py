from datetime import UTC, datetime, timedelta

from custom_components.sensor_guardian.availability.engine import evaluate_health
from custom_components.sensor_guardian.availability.profile import learn_report_profile

NOW = datetime(2025, 1, 10, tzinfo=UTC)
PROFILE = {
    "pattern_confidence": 0.9,
    "p90_interval_seconds": 60,
    "p95_interval_seconds": 100,
}


def test_startup_grace_and_event_only_never_false_offline():
    initializing = evaluate_health(
        now=NOW,
        startup_at=NOW - timedelta(seconds=30),
        last_reported=None,
        profile=PROFILE,
    )
    assert initializing["state"] == "initializing"
    event_only = evaluate_health(
        now=NOW,
        startup_at=NOW - timedelta(days=5),
        last_reported=NOW - timedelta(days=3),
        profile=learn_report_profile([]),
    )
    assert event_only["state"] == "unknown"


def test_per_device_pattern_drives_degraded_stale_offline_thresholds():
    kwargs = {"startup_at": NOW - timedelta(days=1), "profile": PROFILE}
    assert (
        evaluate_health(now=NOW, last_reported=NOW - timedelta(seconds=130), **kwargs)[
            "state"
        ]
        == "degraded"
    )
    assert (
        evaluate_health(now=NOW, last_reported=NOW - timedelta(seconds=200), **kwargs)[
            "state"
        ]
        == "stale"
    )
    assert (
        evaluate_health(now=NOW, last_reported=NOW - timedelta(seconds=1200), **kwargs)[
            "state"
        ]
        == "offline"
    )


def test_native_availability_and_recovery_window_have_precedence():
    assert (
        evaluate_health(
            now=NOW,
            startup_at=NOW,
            last_reported=None,
            profile={},
            native_available=False,
        )["state"]
        == "offline"
    )
    recovering = evaluate_health(
        now=NOW,
        startup_at=NOW,
        last_reported=None,
        profile={},
        native_available=True,
        previous_state="offline",
        recovery_started_at=NOW - timedelta(seconds=30),
    )
    assert recovering["state"] == "recovering"
    healthy = evaluate_health(
        now=NOW,
        startup_at=NOW,
        last_reported=None,
        profile={},
        native_available=True,
        previous_state="offline",
        recovery_started_at=NOW - timedelta(minutes=3),
    )
    assert healthy["state"] == "healthy"


async def test_source_state_availability_without_a_periodic_report_profile(hass):
    from unittest.mock import AsyncMock

    from custom_components.sensor_guardian.models import empty_store_data
    from custom_components.sensor_guardian.runtime import async_process_devices

    data = empty_store_data()
    data["devices"].append(
        {
            "device_id": "socket",
            "tracking_mode": "availability_only",
            "power_type": "mains",
            "sentinels": ["switch.socket"],
            "entity_refs": {},
        }
    )
    runtime = {
        "data": data,
        "startup_at": NOW - timedelta(days=1),
        "storage": type("Storage", (), {"async_save": AsyncMock()})(),
    }
    # A switched-off socket still communicates; off is not offline.
    hass.states.async_set("switch.socket", "off")
    await async_process_devices(hass, runtime, now=NOW)
    assert data["devices"][0]["health_state"] == "healthy"
    hass.states.async_set("switch.socket", "unavailable")
    await async_process_devices(hass, runtime, now=NOW)
    assert data["devices"][0]["health_state"] == "offline"
    assert data["devices"][0]["cause"] == "unknown"
