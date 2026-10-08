from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sensor_guardian.models import empty_store_data
from custom_components.sensor_guardian.storage import GuardianStorage


async def test_prevention_reads_preserve_nulls_and_stock_writes(
    hass, hass_storage, hass_ws_client
):
    data = empty_store_data()
    data["settings"]["tracking_receipts"] = {"private": {"device_id": "hidden"}}
    data["devices"].append(
        {
            "device_id": "d",
            "name": "Sensor",
            "tracking_mode": "battery_only",
            "power_type": "replaceable_battery",
            "entity_refs": {},
        }
    )
    entry = MockConfigEntry(domain="sensor_guardian", data={}, unique_id="global")
    entry.add_to_hass(hass)
    storage = GuardianStorage(hass, entry.entry_id)
    hass_storage[storage.key] = {"version": 1, "minor_version": 2, "data": data}
    assert await hass.config_entries.async_setup(entry.entry_id)
    client = await hass_ws_client()
    await client.send_json_auto_id({"type": "sensor_guardian/get_dashboard"})
    response = await client.receive_json()
    assert response["success"]
    assert response["result"]["counts"]["total"] == 1
    assert response["result"]["meta"]["backend_version"]
    await client.send_json_auto_id(
        {"type": "sensor_guardian/get_device_detail", "device_id": "d", "days": 7}
    )
    response = await client.receive_json()
    assert response["success"]
    assert response["result"]["device"]["battery_level"] is None
    assert "tracking_receipts" not in response["result"]["inherited_rules"]
    for active in (False, False, True, True):
        await client.send_json_auto_id(
            {
                "type": "sensor_guardian/set_tracking_active",
                "device_id": "d",
                "active": active,
            }
        )
        assert (await client.receive_json())["success"]
    runtime = hass.data["sensor_guardian"][entry.entry_id]
    assert runtime["data"]["devices"][0]["tracking_mode"] == "battery_only"
    await client.send_json_auto_id(
        {
            "type": "sensor_guardian/save_stock",
            "battery_type": "AAA",
            "on_hand": 8,
            "minimum": 4,
        }
    )
    assert (await client.receive_json())["success"]
    await client.send_json_auto_id({"type": "sensor_guardian/get_stock"})
    response = await client.receive_json()
    assert (
        next(
            row for row in response["result"]["items"] if row["battery_type"] == "AAA"
        )["on_hand"]
        == 8
    )
    await client.close()
    await hass.config_entries.async_unload(entry.entry_id)


async def test_onboarding_preview_apply_is_idempotent_and_excludes_resolved(
    hass, hass_storage, hass_ws_client
):
    from homeassistant.helpers import device_registry as dr
    from homeassistant.helpers import entity_registry as er

    source = MockConfigEntry(domain="zha", data={})
    source.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=source.entry_id,
        identifiers={("zha", "native")},
        name="Door",
    )
    row = er.async_get(hass).async_get_or_create(
        "sensor",
        "zha",
        "battery",
        device_id=device.id,
        config_entry=source,
        original_name="Battery",
        original_device_class="battery",
        unit_of_measurement="%",
    )
    hass.states.async_set(
        row.entity_id, "45", {"device_class": "battery", "unit_of_measurement": "%"}
    )
    entry = MockConfigEntry(domain="sensor_guardian", data={}, unique_id="global")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    client = await hass_ws_client()
    await client.send_json_auto_id(
        {"type": "sensor_guardian/preview_tracking", "device_ids": [device.id]}
    )
    response = await client.receive_json()
    assert response["success"]
    preview_id = response["result"]["preview_id"]
    for _ in range(2):
        await client.send_json_auto_id(
            {"type": "sensor_guardian/apply_tracking", "preview_id": preview_id}
        )
        result = await client.receive_json()
        assert result["success"]
        assert result["result"]["results"][0]["status"] == "tracked"
    runtime = hass.data["sensor_guardian"][entry.entry_id]
    assert len(runtime["data"]["devices"]) == 1
    assert runtime["data"]["devices"][0]["source_integration"] == "zha"
    other = dr.async_get(hass).async_get_or_create(
        config_entry_id=source.entry_id,
        identifiers={("zha", "other")},
        name="Other",
    )
    foreign = er.async_get(hass).async_get_or_create(
        "sensor",
        "zha",
        "foreign-battery",
        device_id=other.id,
        config_entry=source,
        original_name="Battery",
        original_device_class="battery",
        unit_of_measurement="%",
    )
    await client.send_json_auto_id(
        {
            "type": "sensor_guardian/update_sources",
            "device_id": device.id,
            "entity_refs": {"battery_level": foreign.entity_id},
            "availability_entity": row.entity_id,
        }
    )
    rejected = await client.receive_json()
    assert rejected["success"] is False
    assert rejected["error"]["code"] == "invalid_source"
    assert (
        runtime["data"]["devices"][0]["entity_refs"]["battery_level"] == row.entity_id
    )
    await client.close()
    await hass.config_entries.async_unload(entry.entry_id)
