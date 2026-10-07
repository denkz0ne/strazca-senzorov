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
