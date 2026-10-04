from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.sensor_guardian import discovery_notifier


@pytest.mark.parametrize("count", [1, 4])
async def test_notice_is_one_native_badge_with_exact_pending_count(
    hass, monkeypatch, count
):
    runtime = {"data": {"devices": [], "settings": {}}}
    hass.data["sensor_guardian"] = {"entry": runtime}
    monkeypatch.setattr(
        discovery_notifier,
        "async_discover_devices",
        AsyncMock(return_value=[{"device_id": str(i)} for i in range(count)]),
    )
    create = MagicMock()
    monkeypatch.setattr(discovery_notifier, "async_create", create)

    assert await discovery_notifier.async_refresh_discovery_notice(hass) == count
    assert runtime["discovery_pending_count"] == count
    create.assert_called_once()
    assert f"**{count}**" in create.call_args.args[1]
    assert (
        create.call_args.kwargs["notification_id"] == discovery_notifier.NOTIFICATION_ID
    )


async def test_notice_is_dismissed_when_pending_queue_is_empty(hass, monkeypatch):
    hass.data["sensor_guardian"] = {"entry": {"data": {"devices": [], "settings": {}}}}
    monkeypatch.setattr(
        discovery_notifier, "async_discover_devices", AsyncMock(return_value=[])
    )
    dismiss = MagicMock()
    monkeypatch.setattr(discovery_notifier, "async_dismiss", dismiss)

    assert await discovery_notifier.async_refresh_discovery_notice(hass) == 0
    dismiss.assert_called_once_with(hass, discovery_notifier.NOTIFICATION_ID)


@pytest.mark.parametrize(
    ("event_type", "event_data"),
    [
        ("device_registry_updated", {"action": "create", "device_id": "d1"}),
        (
            "entity_registry_updated",
            {"action": "create", "entity_id": "sensor.d1_battery"},
        ),
    ],
)
async def test_registry_changes_refresh_the_pending_notification(
    hass, monkeypatch, event_type, event_data
):
    refresh = AsyncMock(return_value=1)
    monkeypatch.setattr(discovery_notifier, "async_refresh_discovery_notice", refresh)
    discovery_notifier.async_register_discovery_listeners(hass)

    hass.bus.async_fire(event_type, event_data)
    await hass.async_block_till_done()

    refresh.assert_awaited_once_with(hass)
