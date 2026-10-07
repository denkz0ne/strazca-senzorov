from types import SimpleNamespace

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sensor_guardian.discovery import (
    display_identifier,
    rank_device_entities,
)


def entity(
    entity_id,
    domain="sensor",
    *,
    name=None,
    unit=None,
    device_class=None,
    disabled_by=None,
):
    return SimpleNamespace(
        entity_id=entity_id,
        domain=domain,
        original_name=name,
        unique_id=entity_id,
        unit_of_measurement=unit,
        device_class=device_class,
        disabled_by=disabled_by,
    )


def test_ranks_battery_and_availability_with_disabled_signal_recommendation():
    candidate = rank_device_entities(
        "d1",
        [
            entity("sensor.door_battery", unit="%"),
            entity(
                "binary_sensor.door_connectivity",
                "binary_sensor",
                device_class="connectivity",
            ),
            entity("sensor.door_linkquality", disabled_by="integration"),
        ],
    )
    assert candidate is not None
    assert candidate.suggested_mode == "battery_and_availability"
    assert candidate.recommended_signal_entities == ("sensor.door_linkquality",)
    assert candidate.entity_refs["battery_level"] == "sensor.door_battery"


def test_event_only_candidate_with_unknown_type_is_not_forced():
    assert rank_device_entities("d2", [entity("sensor.door_temperature")]) is None


def test_battery_only_candidate_and_manual_dismissal_data_shape():
    candidate = rank_device_entities("d3", [entity("sensor.sensor_battery", unit="%")])
    assert candidate is not None
    assert candidate.suggested_mode == "battery_and_availability"
    assert candidate.confidence == "high"


def test_friendly_identifier_is_name_only_and_accepts_zb_and_zbt_patterns():
    assert display_identifier("zbt05-kupelna") == "ZBT05"
    assert display_identifier("zbt-5 teplomer") == "ZBT05"
    assert display_identifier("ZB123 entry") == "ZB123"
    assert display_identifier("registry-5a4d") == ""
    assert display_identifier("device ZB1234") == ""


def test_native_percentage_device_class_is_never_a_binary_low_flag():
    for entity_id in ("sensor.remote_battery", "sensor.detektor_bateria"):
        candidate = rank_device_entities(
            "d1", [entity(entity_id, unit="%", device_class="battery")]
        )
        assert candidate.entity_refs["battery_level"] == entity_id
        assert candidate.entity_refs["battery_low"] is None


def test_runtime_sources_exclude_battery_notes_and_guardian_helpers():
    helper = entity("sensor.battery_plus", unit="%", device_class="battery")
    helper.platform = "battery_notes"
    guardian = entity("binary_sensor.guardian_battery_attention", "binary_sensor")
    guardian.platform = "sensor_guardian"
    native = entity("sensor.bateria", unit="%", device_class="battery")
    native.platform = "zha"
    candidate = rank_device_entities("d1", [helper, guardian, native])
    assert candidate.entity_refs["battery_level"] == "sensor.bateria"
    assert candidate.entity_refs["battery_low"] is None


def test_mains_voltage_and_switch_are_availability_not_battery_evidence():
    voltage = entity("sensor.socket_voltage", unit="V", device_class="voltage")
    voltage.platform = "mqtt"
    switch = entity("switch.socket", domain="switch")
    switch.platform = "mqtt"
    candidate = rank_device_entities("d1", [voltage, switch])
    assert candidate.suggested_mode == "availability_only"
    assert candidate.entity_refs["voltage"] is None


async def test_discovery_uses_friendly_registry_metadata_and_hides_resolved_devices(
    hass,
):
    from homeassistant.helpers import area_registry
    from homeassistant.helpers import device_registry as dr
    from homeassistant.helpers import entity_registry as er

    from custom_components.sensor_guardian.discovery import async_discover_devices

    source_entry = MockConfigEntry(domain="zha", data={})
    source_entry.add_to_hass(hass)
    area = area_registry.async_get(hass).async_create("Kúpeľňa")
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=source_entry.entry_id,
        identifiers={("zha", "zbt05")},
        name="zbt05-kupelna",
        manufacturer="Example",
        model="Thermometer",
    )
    dr.async_get(hass).async_update_device(device.id, area_id=area.id)
    entity_row = er.async_get(hass).async_get_or_create(
        "sensor",
        "zha",
        "battery",
        config_entry=source_entry,
        device_id=device.id,
        original_name="Battery",
        unit_of_measurement="%",
    )
    hass.states.async_set(entity_row.entity_id, "80", {"unit_of_measurement": "%"})

    candidates = await async_discover_devices(hass)
    candidate = next(item for item in candidates if item["device_id"] == device.id)
    assert candidate["name"] == "zbt05-kupelna"
    assert candidate["identifier"] == "ZBT05"
    assert candidate["area_name"] == "Kúpeľňa"
    assert candidate["source_integration"] == "zha"
    assert await async_discover_devices(hass, tracked_device_ids={device.id}) == []
