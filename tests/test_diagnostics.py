"""Support evidence excludes private source identities."""

import json
from types import SimpleNamespace

from custom_components.sensor_guardian.diagnostics import (
    async_get_config_entry_diagnostics,
)
from custom_components.sensor_guardian.models import empty_store_data


async def test_diagnostics_report_coverage_without_names_or_entity_ids(hass):
    data = empty_store_data()
    data["devices"].append(
        {
            "device_id": "private-id",
            "name": "Private room",
            "entity_refs": {"battery_level": "sensor.private_battery"},
            "recommended_signal_entities": ["sensor.private_lqi"],
        }
    )
    hass.data["sensor_guardian"] = {"entry": {"data": data}}
    result = await async_get_config_entry_diagnostics(
        hass, SimpleNamespace(entry_id="entry")
    )
    assert result["device_count"] == 1
    assert result["devices"][0]["source_coverage"]["battery_level"]
    assert result["devices"][0]["disabled_signal_count"] == 1
    assert "private" not in json.dumps(result).lower()
