"""User-visible alerts follow deduplicated incident transitions."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from custom_components.sensor_guardian import runtime as runtime_module
from custom_components.sensor_guardian.models import empty_store_data


async def test_one_outage_notification_then_dismissal_after_stable_recovery(
    hass, monkeypatch
):
    create, dismiss = MagicMock(), MagicMock()
    monkeypatch.setattr(runtime_module, "async_create", create, raising=False)
    monkeypatch.setattr(runtime_module, "async_dismiss", dismiss, raising=False)
    now = datetime.now(UTC)
    data = empty_store_data()
    data["devices"].append(
        {
            "device_id": "socket",
            "name": "Zásuvka SERVER",
            "tracking_mode": "availability_only",
            "power_type": "mains",
            "sentinels": ["switch.socket"],
            "entity_refs": {},
        }
    )
    runtime = {
        "data": data,
        "startup_at": now - timedelta(days=1),
        "storage": type("Storage", (), {"async_save": AsyncMock()})(),
    }
    hass.states.async_set("switch.socket", "unavailable")
    await runtime_module.async_process_devices(hass, runtime, now=now)
    await runtime_module.async_process_devices(
        hass, runtime, now=now + timedelta(seconds=1)
    )
    create.assert_called_once()
    assert "Zásuvka SERVER" in create.call_args.args[1]
    assert "nepotvrdená" in create.call_args.args[1]
    hass.states.async_set("switch.socket", "off")
    await runtime_module.async_process_devices(
        hass, runtime, now=now + timedelta(seconds=2)
    )
    await runtime_module.async_process_devices(
        hass, runtime, now=now + timedelta(minutes=3)
    )
    dismiss.assert_called_once()


async def test_dropout_uses_recent_battery_evidence_but_rejects_stale_history(
    hass, monkeypatch
):
    monkeypatch.setattr(runtime_module, "async_create", MagicMock())
    now = datetime.now(UTC)
    for age, expected in ((1, "battery"), (8, "unknown")):
        data = empty_store_data()
        data["devices"].append(
            {
                "device_id": "battery",
                "tracking_mode": "battery_and_availability",
                "power_type": "replaceable_battery",
                "sentinels": ["sensor.battery"],
                "entity_refs": {"battery_level": "sensor.battery"},
            }
        )
        data["samples"].append(
            {
                "sample_id": "s",
                "device_id": "battery",
                "timestamp": (now - timedelta(days=age)).isoformat(),
                "level_percent": 5,
                "native_low": True,
            }
        )
        runtime = {
            "data": data,
            "startup_at": now - timedelta(days=1),
            "storage": type("Storage", (), {"async_save": AsyncMock()})(),
        }
        hass.states.async_set("sensor.battery", "unavailable")
        await runtime_module.async_process_devices(hass, runtime, now=now)
        assert data["devices"][0]["cause"] == expected


async def test_notifications_can_be_disabled_without_disabling_events(
    hass, monkeypatch
):
    create = MagicMock()
    monkeypatch.setattr(runtime_module, "async_create", create)
    now = datetime.now(UTC)
    data = empty_store_data()
    data["settings"]["notifications_enabled"] = False
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
        "startup_at": now - timedelta(days=1),
        "storage": type("Storage", (), {"async_save": AsyncMock()})(),
    }
    events = []
    hass.bus.async_listen(
        "sensor_guardian_incident", lambda event: events.append(event.data)
    )
    hass.states.async_set("switch.socket", "unavailable")
    await runtime_module.async_process_devices(hass, runtime, now=now)
    await hass.async_block_till_done()
    assert len(events) == 1
    create.assert_not_called()
