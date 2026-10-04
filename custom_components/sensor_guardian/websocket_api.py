"""Authenticated, paginated API for the Sensor Guardian panel."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.components.websocket_api.connection import ActiveConnection
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import Unauthorized
from homeassistant.helpers import device_registry, entity_registry
from homeassistant.helpers.storage import Store

from .const import DOMAIN
from .discovery import display_identifier
from .migration.battery_notes import (
    apply_import_preview,
    async_build_import_preview,
)
from .models import StorageDataError
from .runtime import _merge_data

PAGE_MAX = 100
SECTIONS = {"overview", "batteries", "devices", "discovery", "incidents", "settings"}
TRACKING_MODES = {
    "battery_and_availability",
    "availability_only",
    "battery_only",
}
POWER_TYPES = {"replaceable_battery", "rechargeable", "mains", "unknown"}
BATTERY_POWER_TYPES = {"replaceable_battery", "rechargeable", "unknown"}

OVERVIEW_FIELDS = (
    "device_id",
    "name",
    "area_id",
    "health_state",
    "cause",
    "cause_confidence",
    "tracking_mode",
    "power_type",
    "last_reported_at",
    "battery_attention",
    "active_incident_ids",
    "source_integration",
    "area_name",
    "transport",
    "battery_type",
    "battery_quantity",
    "battery_estimate",
    "health_reason",
    "recommended_signal_entities",
)
DEVICE_FIELDS = (
    *OVERVIEW_FIELDS,
    "source_integration",
    "config_entry_id",
    "transport",
    "manufacturer",
    "model",
    "model_id",
    "battery_type",
    "battery_quantity",
    "battery_estimate",
    "entity_refs",
    "signal",
    "recommended_signal_entities",
    "health_reason",
    "health_since",
    "native_availability_state",
    "parent_incident_id",
    "snoozed_until",
    "area_name",
    "battery_level",
    "battery_low",
    "voltage",
    "voltage_unit",
)
MODEL_FIELDS = (
    "model_id",
    "manufacturer",
    "model",
    "model_ids",
    "hardware_versions",
    "aliases",
    "default_battery_type",
    "default_battery_quantity",
    "power_hint",
    "replaceable",
    "source",
)
INCIDENT_FIELDS = (
    "incident_id",
    "device_ids",
    "opened_at",
    "updated_at",
    "closed_at",
    "health_state",
    "cause",
    "cause_confidence",
    "cause_history",
    "evidence",
    "severity",
    "acknowledged",
    "snoozed_until",
    "parent_incident_id",
)
SETTING_FIELDS = {
    "startup_grace_minutes",
    "low_battery_threshold",
    "replacement_warning_days",
    "offline_multiplier",
    "stale_multiplier",
    "recovery_stability_minutes",
    "notification_cooldown_minutes",
    "history_window_days",
}


def _pick(record: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    """Copy only allowed keys from a stored record."""
    return {key: deepcopy(record[key]) for key in fields if key in record}


def _matches(record: dict[str, Any], query: str) -> bool:
    """Match a simple case-insensitive search without inspecting hidden fields."""
    if not query:
        return True
    text = " ".join(
        str(value)
        for key, value in record.items()
        if key not in {"entity_refs", "signal", "evidence"}
    )
    return query.casefold() in text.casefold()


def _enrich_panel_items(
    hass: HomeAssistant, data: dict[str, Any], result: dict[str, Any]
) -> None:
    """Add friendly registry names and selected live readings to curated rows."""
    from homeassistant.helpers import area_registry, device_registry

    devices = device_registry.async_get(hass)
    areas = area_registry.async_get(hass)
    tracked = {item.get("device_id"): item for item in data.get("devices", [])}
    for row in result.get("items", []):
        device_id = row.get("device_id")
        entry = devices.async_get(device_id) if isinstance(device_id, str) else None
        area_id = row.get("area_id") or (entry.area_id if entry else None)
        area = areas.async_get_area(area_id) if area_id else None
        row["area_name"] = area.name if area else None
        if entry:
            row["name"] = (
                entry.name_by_user or entry.name or row.get("name") or "Neznámy názov"
            )
            row["manufacturer"] = row.get("manufacturer") or entry.manufacturer
            row["model"] = row.get("model") or entry.model
        row["identifier"] = display_identifier(row.get("name"))
        source = tracked.get(device_id, {})
        cycle = next(
            (
                item
                for item in reversed(data.get("cycles", []))
                if item.get("device_id") == device_id
            ),
            None,
        )
        row["last_replaced_at"] = cycle.get("started_at") if cycle else None
        device_samples = [
            sample
            for sample in reversed(data.get("samples", []))
            if sample.get("device_id") == device_id
        ]
        for key, output in (
            ("level_percent", "battery_level"),
            ("native_low", "battery_low"),
            ("voltage", "voltage"),
        ):
            sample = next(
                (item for item in device_samples if item.get(key) is not None), None
            )
            if output not in row and sample is not None:
                row[output] = sample[key]
        refs = source.get("entity_refs", {})
        if isinstance(refs, dict):
            for key, output in (
                ("battery_level", "battery_level"),
                ("battery_low", "battery_low"),
                ("voltage", "voltage"),
            ):
                entity_id = refs.get(key)
                state = (
                    hass.states.get(entity_id) if isinstance(entity_id, str) else None
                )
                if state is not None and state.state not in {"unknown", "unavailable"}:
                    value: Any = state.state
                    if key == "battery_low":
                        value = state.state == "on"
                    elif key in {"battery_level", "voltage"}:
                        try:
                            value = float(state.state)
                        except ValueError:
                            continue
                    row[output] = value
                    if key == "voltage":
                        row["voltage_unit"] = state.attributes.get(
                            "unit_of_measurement"
                        )
        signal_values = []
        for signal in source.get("signal", []):
            entity_id = signal.get("entity_id") if isinstance(signal, dict) else None
            state = hass.states.get(entity_id) if isinstance(entity_id, str) else None
            if state is not None and state.state not in {"unknown", "unavailable"}:
                signal_values.append(
                    {"kind": signal.get("kind", "signal"), "value": state.state}
                )
        if signal_values:
            row["signal_values"] = signal_values


def get_section_page(
    data: dict[str, Any],
    section: str,
    *,
    offset: int = 0,
    limit: int = 50,
    query: str = "",
    candidates: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a bounded response and redact storage-only fields."""
    if section not in SECTIONS:
        raise vol.Invalid("Unknown panel section")
    if not 0 <= offset <= 1_000_000:
        raise vol.Invalid("Offset is outside supported bounds")
    if not 1 <= limit <= PAGE_MAX:
        raise vol.Invalid(f"Page size must be between 1 and {PAGE_MAX}")

    if section in {"overview", "devices"}:
        fields = OVERVIEW_FIELDS if section == "overview" else DEVICE_FIELDS
        records = [_pick(record, fields) for record in data.get("devices", [])]
        records = [record for record in records if _matches(record, query)]
    elif section == "batteries":
        records = [_pick(record, MODEL_FIELDS) for record in data.get("models", [])]
        records = [record for record in records if _matches(record, query)]
    elif section == "incidents":
        records = [
            _pick(record, INCIDENT_FIELDS) for record in data.get("incidents", [])
        ]
        records = [record for record in records if _matches(record, query)]
    elif section == "discovery":
        records = deepcopy(candidates or [])
        records = [record for record in records if _matches(record, query)]
    else:
        settings = data.get("settings", {})
        safe_settings = {
            key: deepcopy(value)
            for key, value in settings.items()
            if key in SETTING_FIELDS
        }
        return {
            "section": section,
            "settings": safe_settings,
            "migration": {
                "receipt_count": len(settings.get("migration_receipts", {})),
                "unmatched_import_count": len(
                    settings.get("unmatched_import_records", [])
                ),
            },
        }

    total = len(records)
    items = records[offset : offset + limit]
    result = {
        "section": section,
        "items": items,
        "total": total,
        "offset": offset,
        "limit": limit,
        "has_more": offset + len(items) < total,
    }
    if section == "discovery":
        result["filters"] = {
            "integrations": sorted(
                {str(item.get("source_integration") or "unknown") for item in records}
            ),
            "areas": sorted({str(item.get("area_name") or "—") for item in records}),
            "availability": sorted(
                {str(item.get("availability_state") or "unknown") for item in records}
            ),
        }
    if section == "batteries":
        cycles = data.get("cycles", [])
        tracked_devices = [
            _pick(
                device,
                (
                    "device_id",
                    "name",
                    "manufacturer",
                    "model",
                    "model_id",
                    "battery_type",
                    "battery_quantity",
                    "battery_estimate",
                    "last_replaced_at",
                    "power_type",
                    "health_state",
                    "battery_attention",
                    "battery_level",
                    "native_battery_low",
                ),
            )
            for device in data.get("devices", [])
            if device.get("tracking_mode")
            in {"battery_and_availability", "battery_only"}
        ]
        for device in tracked_devices:
            name = str(device.get("name") or "")
            device["identifier"] = display_identifier(name)
            device_samples = [
                sample
                for sample in reversed(data.get("samples", []))
                if sample.get("device_id") == device.get("device_id")
            ]
            for key, output in (
                ("level_percent", "battery_level"),
                ("native_low", "native_battery_low"),
            ):
                sample = next(
                    (item for item in device_samples if item.get(key) is not None),
                    None,
                )
                device[output] = sample[key] if sample else device.get(output)
            latest_cycle = next(
                (
                    cycle
                    for cycle in reversed(cycles)
                    if cycle.get("device_id") == device.get("device_id")
                ),
                {},
            )
            device["last_replaced_at"] = latest_cycle.get(
                "started_at", device.get("last_replaced_at")
            )
        tracked_devices = [
            device for device in tracked_devices if _matches(device, query)
        ]
        result["related"] = {
            "cycle_count": len(cycles),
            "tracked_device_count": len(tracked_devices),
            "tracked_devices": tracked_devices[offset : offset + limit],
            "tracked_devices_has_more": offset + limit < len(tracked_devices),
            "cycles": [
                _pick(
                    cycle,
                    (
                        "cycle_id",
                        "device_id",
                        "started_at",
                        "ended_at",
                        "battery_type",
                        "battery_quantity",
                        "provenance",
                        "replacement_reason",
                    ),
                )
                for cycle in cycles[-100:]
            ],
        }
        result["has_more"] = (
            result["has_more"] or result["related"]["tracked_devices_has_more"]
        )
    return result


def merge_bundled_models(data: dict[str, Any], bundled: list[dict[str, Any]]) -> int:
    """Seed missing bundled records while preserving local edits and overrides."""
    models = data.setdefault("models", [])
    existing = {item.get("model_id") for item in models}
    added = 0
    for model in bundled:
        model_id = model.get("model_id")
        if isinstance(model_id, str) and model_id not in existing:
            models.append(deepcopy(model))
            existing.add(model_id)
            added += 1
    return added


def add_local_model(
    data: dict[str, Any],
    *,
    manufacturer: str,
    model: str,
    battery_type: str,
    battery_quantity: int,
    power_type: str,
) -> dict[str, Any]:
    """Add a user-authored catalogue row with a deterministic local ID."""
    values = [manufacturer.strip(), model.strip(), battery_type.strip()]
    if not all(values):
        raise vol.Invalid("Manufacturer, model and battery type are required")
    if not 1 <= battery_quantity <= 20 or power_type not in BATTERY_POWER_TYPES:
        raise vol.Invalid("Battery quantity or power type is invalid")
    normalized = [value.casefold() for value in values]
    if any(
        [
            str(item.get("manufacturer") or "").casefold(),
            str(item.get("model") or "").casefold(),
            str(item.get("default_battery_type") or "").casefold(),
            item.get("default_battery_quantity", 1),
        ]
        == [*normalized, battery_quantity]
        for item in data.setdefault("models", [])
    ):
        raise vol.Invalid("This manufacturer and model already exist in the catalogue")
    identity = json.dumps(
        [*normalized, battery_quantity, power_type], separators=(",", ":")
    ).encode("utf-8")
    battery_model: dict[str, Any] = {
        "model_id": f"local_{hashlib.sha256(identity).hexdigest()[:20]}",
        "manufacturer": values[0],
        "model": values[1],
        "model_ids": [],
        "hardware_versions": [],
        "default_battery_type": values[2],
        "default_battery_quantity": battery_quantity,
        "power_hint": power_type,
        "replaceable": power_type == "replaceable_battery",
        "source": "local",
    }
    data["models"].append(battery_model)
    return battery_model


def apply_battery_assignment(
    device: dict[str, Any],
    *,
    battery_type: str,
    battery_quantity: int,
    power_type: str,
    model_id: str | None = None,
) -> None:
    """Apply a per-device choice without changing the shared model row."""
    if device.get("tracking_mode") not in {"battery_and_availability", "battery_only"}:
        raise vol.Invalid("Device is not configured for battery tracking")
    if not battery_type.strip() or not 1 <= battery_quantity <= 20:
        raise vol.Invalid("Battery type and a quantity from 1 to 20 are required")
    if power_type not in BATTERY_POWER_TYPES:
        raise vol.Invalid("Battery power type is invalid")
    device["battery_type"] = battery_type.strip()
    device["battery_quantity"] = battery_quantity
    device["power_type"] = power_type
    if model_id is not None:
        device["model_id"] = model_id
    overrides = device.setdefault("user_overrides", {})
    overrides.update(
        {
            "battery_type": device["battery_type"],
            "battery_quantity": battery_quantity,
            "power_type": power_type,
        }
    )


def load_bundled_models() -> list[dict[str, Any]]:
    """Read the bundled converted catalogue without network access."""
    path = Path(__file__).parent / "data" / "battery_models.json"
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as err:
        raise StorageDataError(
            f"Cannot read the bundled model catalogue: {err}"
        ) from err
    models = raw.get("models") if isinstance(raw, dict) else None
    if not isinstance(models, list) or any(
        not isinstance(item, dict) for item in models
    ):
        raise StorageDataError("The bundled model catalogue has an invalid shape")
    return models


def async_register_commands(hass: HomeAssistant) -> None:
    """Register authenticated read/write commands once during component setup."""

    @websocket_api.websocket_command(
        {
            vol.Required("type"): f"{DOMAIN}/get_data",
            vol.Required("section"): vol.In(SECTIONS),
            vol.Optional("offset", default=0): vol.All(
                vol.Coerce(int), vol.Range(min=0, max=1_000_000)
            ),
            vol.Optional("limit", default=50): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=PAGE_MAX)
            ),
            vol.Optional("query", default=""): vol.All(str, vol.Length(max=200)),
        }
    )
    @websocket_api.async_response
    async def ws_get_data(hass, connection, msg):
        _require_admin(connection)
        runtime = _get_runtime(hass)
        candidates = None
        if msg["section"] == "discovery":
            from .discovery import async_discover_devices

            dismissed = set(runtime["data"]["settings"].get("dismissed_device_ids", []))
            tracked = {item["device_id"] for item in runtime["data"]["devices"]}
            candidates = await async_discover_devices(
                hass, tracked_device_ids=tracked, dismissed_device_ids=dismissed
            )
            for candidate in candidates:
                matched = next(
                    (
                        model
                        for model in runtime["data"].get("models", [])
                        if str(model.get("manufacturer") or "").casefold()
                        == str(candidate.get("manufacturer") or "").casefold()
                        and str(model.get("model") or "").casefold()
                        == str(candidate.get("model") or "").casefold()
                    ),
                    None,
                )
                if matched:
                    candidate["battery_type"] = matched.get("default_battery_type")
                    candidate["battery_quantity"] = matched.get(
                        "default_battery_quantity"
                    )
                    candidate["matched_model_id"] = matched.get("model_id")
        result = get_section_page(
            runtime["data"],
            msg["section"],
            offset=msg["offset"],
            limit=msg["limit"],
            query=msg["query"],
            candidates=candidates,
        )
        _enrich_panel_items(hass, runtime["data"], result)
        connection.send_result(msg["id"], result)

    @websocket_api.websocket_command(
        {
            vol.Required("type"): f"{DOMAIN}/import_preview",
        }
    )
    @websocket_api.async_response
    async def ws_import_preview(hass, connection, msg):
        _require_admin(connection)
        runtime = _get_runtime(hass)
        registry = device_registry.async_get(hass)
        preview = await async_build_import_preview(
            hass,
            existing_data=runtime["data"],
            device_ids=set(registry.devices),
        )
        source_store, source_entries = await _read_battery_notes_source(hass)
        preview["source_available"] = source_store is not None or bool(source_entries)
        runtime["import_preview"] = preview
        summary = {
            "source_available": preview["source_available"],
            "catalogue_model_count": preview["catalogue_model_count"],
            "matched_device_count": preview["matched_device_count"],
            "unmatched_count": preview["unmatched_count"],
            "cycle_count": len(preview["cycles"]),
            "sample_count": len(preview["samples"]),
            "receipt_id": preview["receipt_id"],
            "history_note": preview["history_note"],
        }
        connection.send_result(msg["id"], summary)

    @websocket_api.websocket_command(
        {
            vol.Required("type"): f"{DOMAIN}/import_apply",
            vol.Required("receipt_id"): vol.All(str, vol.Length(min=1, max=100)),
        }
    )
    @websocket_api.async_response
    async def ws_import_apply(hass, connection, msg):
        _require_admin(connection)
        runtime = _get_runtime(hass)
        preview = runtime.get("import_preview")
        if (
            not isinstance(preview, dict)
            or preview.get("receipt_id") != msg["receipt_id"]
        ):
            raise vol.Invalid("Create and review the current import preview first")
        if not preview.get("source_available"):
            raise vol.Invalid("Battery Notes is not available as a migration source")
        updated, backup = apply_import_preview(runtime["data"], preview)
        entry_id = next(
            key for key, item in hass.data[DOMAIN].items() if item is runtime
        )
        backup_store = Store(
            hass,
            1,
            f"{DOMAIN}.{entry_id}.battery_notes_backup",
            private=True,
            atomic_writes=True,
        )
        await backup_store.async_save(backup)
        await runtime["storage"].async_save(updated)
        _merge_data(runtime, updated)
        runtime.pop("import_preview", None)
        connection.send_result(
            msg["id"],
            {
                "applied": True,
                "receipt_id": preview["receipt_id"],
                "backup_saved": True,
            },
        )

    @websocket_api.websocket_command(
        {
            vol.Required("type"): f"{DOMAIN}/track_device",
            vol.Required("device_id"): str,
            vol.Required("tracking_mode"): vol.In(TRACKING_MODES),
            vol.Required("power_type"): vol.In(POWER_TYPES),
        }
    )
    @websocket_api.async_response
    async def ws_track_device(hass, connection, msg):
        _require_admin(connection)
        runtime = _get_runtime(hass)
        data = runtime["data"]
        if any(item["device_id"] == msg["device_id"] for item in data["devices"]):
            raise vol.Invalid("Device is already tracked")
        from .discovery import async_discover_devices

        candidates = await async_discover_devices(hass)
        candidate = next(
            (item for item in candidates if item["device_id"] == msg["device_id"]), None
        )
        if candidate is None:
            raise vol.Invalid("Device is not a current discovery candidate")
        mode, power_type = msg["tracking_mode"], msg["power_type"]
        if mode.startswith("battery") and not candidate["suggested_mode"].startswith(
            "battery"
        ):
            raise vol.Invalid("Candidate has no battery evidence")
        if power_type == "mains":
            mode = "availability_only"
        device_registry_value = device_registry.async_get(hass).async_get(
            msg["device_id"]
        )
        source_entities = [
            value for value in candidate["entity_refs"].values() if value
        ]
        entity_registry_value = entity_registry.async_get(hass)
        source_rows = [
            entity_registry_value.async_get(value) for value in source_entities
        ]
        source_row = next((row for row in source_rows if row is not None), None)
        source_integration = source_row.platform if source_row else "unknown"
        transport = {
            "zha": "zigbee",
            "mqtt": "mqtt",
            "esphome": "wifi",
            "bluetooth": "bluetooth",
        }.get(source_integration, "unknown")
        record = {
            "device_id": msg["device_id"],
            "name": (device_registry_value.name_by_user or device_registry_value.name)
            if device_registry_value
            else "Neznámy názov",
            "area_id": device_registry_value.area_id if device_registry_value else None,
            "manufacturer": device_registry_value.manufacturer
            if device_registry_value
            else None,
            "model": device_registry_value.model if device_registry_value else None,
            "source_integration": source_integration,
            "config_entry_id": source_row.config_entry_id if source_row else None,
            "transport": transport,
            "tracking_mode": mode,
            "power_type": power_type,
            "entity_refs": candidate["entity_refs"],
            "sentinels": sorted(set(source_entities + candidate["signal_entities"])),
            "signal": [
                {
                    "entity_id": entity_id,
                    "kind": "rssi" if "rssi" in entity_id.casefold() else "linkquality",
                }
                for entity_id in candidate["signal_entities"]
            ],
            "recommended_signal_entities": candidate["recommended_signal_entities"],
            "health_state": "unknown",
            "cause": "unknown",
            "cause_confidence": "none",
        }
        matching_model = next(
            (
                model
                for model in data["models"]
                if (model.get("manufacturer") or "").casefold()
                == (record.get("manufacturer") or "").casefold()
                and (model.get("model") or "").casefold()
                == (record.get("model") or "").casefold()
            ),
            None,
        )
        if matching_model:
            record["model_id"] = matching_model["model_id"]
            record["battery_type"] = matching_model.get("default_battery_type")
            record["battery_quantity"] = matching_model.get(
                "default_battery_quantity", 1
            )
        data["devices"].append(record)
        dismissed = set(data["settings"].get("dismissed_device_ids", []))
        dismissed.discard(msg["device_id"])
        data["settings"]["dismissed_device_ids"] = sorted(dismissed)
        await runtime["storage"].async_save(data)
        from .discovery_notifier import async_refresh_discovery_notice

        await async_refresh_discovery_notice(hass)
        runtime["refresh_report_subscriptions"]()
        runtime["refresh_battery_subscriptions"]()
        _add_device_entities(hass, runtime, record)
        from .runtime import async_process_devices

        await async_process_devices(hass, runtime)
        connection.send_result(
            msg["id"], {"tracked": True, "device_id": msg["device_id"]}
        )

    @websocket_api.websocket_command(
        {
            vol.Required("type"): f"{DOMAIN}/dismiss_candidate",
            vol.Required("device_id"): str,
        }
    )
    @websocket_api.async_response
    async def ws_dismiss_candidate(hass, connection, msg):
        _require_admin(connection)
        runtime = _get_runtime(hass)
        from .discovery import async_discover_devices

        candidates = await async_discover_devices(hass)
        if not any(item["device_id"] == msg["device_id"] for item in candidates):
            raise vol.Invalid("Device is not a current discovery candidate")
        dismissed = set(runtime["data"]["settings"].get("dismissed_device_ids", []))
        dismissed.add(msg["device_id"])
        runtime["data"]["settings"]["dismissed_device_ids"] = sorted(dismissed)
        await runtime["storage"].async_save(runtime["data"])
        from .discovery_notifier import async_refresh_discovery_notice

        await async_refresh_discovery_notice(hass)
        connection.send_result(
            msg["id"], {"dismissed": True, "device_id": msg["device_id"]}
        )

    @websocket_api.websocket_command(
        {
            vol.Required("type"): f"{DOMAIN}/update_settings",
            vol.Required("values"): {
                vol.Optional("startup_grace_minutes"): vol.All(
                    vol.Coerce(int), vol.Range(min=0, max=1440)
                ),
                vol.Optional("low_battery_threshold"): vol.All(
                    vol.Coerce(float), vol.Range(min=1, max=100)
                ),
                vol.Optional("replacement_warning_days"): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=90)
                ),
                vol.Optional("notification_cooldown_minutes"): vol.All(
                    vol.Coerce(int), vol.Range(min=0, max=10080)
                ),
            },
        }
    )
    @websocket_api.async_response
    async def ws_update_settings(hass, connection, msg):
        _require_admin(connection)
        if not msg["values"]:
            raise vol.Invalid("At least one setting is required")
        runtime = _get_runtime(hass)
        runtime["data"]["settings"].update(msg["values"])
        await runtime["storage"].async_save(runtime["data"])
        connection.send_result(msg["id"], {"updated": sorted(msg["values"])})

    @websocket_api.websocket_command(
        {
            vol.Required("type"): f"{DOMAIN}/add_model",
            vol.Required("manufacturer"): vol.All(str, vol.Length(min=1, max=100)),
            vol.Required("model"): vol.All(str, vol.Length(min=1, max=120)),
            vol.Required("battery_type"): vol.All(str, vol.Length(min=1, max=60)),
            vol.Required("battery_quantity"): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=20)
            ),
            vol.Required("power_type"): vol.In(BATTERY_POWER_TYPES),
        }
    )
    @websocket_api.async_response
    async def ws_add_model(hass, connection, msg):
        _require_admin(connection)
        runtime = _get_runtime(hass)
        model = add_local_model(
            runtime["data"],
            manufacturer=msg["manufacturer"],
            model=msg["model"],
            battery_type=msg["battery_type"],
            battery_quantity=msg["battery_quantity"],
            power_type=msg["power_type"],
        )
        await runtime["storage"].async_save(runtime["data"])
        connection.send_result(
            msg["id"], {"model_id": model["model_id"], "added": True}
        )

    @websocket_api.websocket_command(
        {
            vol.Required("type"): f"{DOMAIN}/update_battery",
            vol.Required("device_id"): str,
            vol.Required("battery_type"): vol.All(str, vol.Length(min=1, max=60)),
            vol.Required("battery_quantity"): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=20)
            ),
            vol.Required("power_type"): vol.In(BATTERY_POWER_TYPES),
            vol.Optional("model_id"): str,
        }
    )
    @websocket_api.async_response
    async def ws_update_battery(hass, connection, msg):
        _require_admin(connection)
        runtime = _get_runtime(hass)
        device = next(
            (
                item
                for item in runtime["data"]["devices"]
                if item["device_id"] == msg["device_id"]
            ),
            None,
        )
        if device is None:
            raise vol.Invalid("Device is not tracked")
        model_id = msg.get("model_id")
        if model_id is not None and not any(
            item["model_id"] == model_id for item in runtime["data"]["models"]
        ):
            raise vol.Invalid("Unknown battery model ID")
        apply_battery_assignment(
            device,
            battery_type=msg["battery_type"],
            battery_quantity=msg["battery_quantity"],
            power_type=msg["power_type"],
            model_id=model_id,
        )
        await runtime["storage"].async_save(runtime["data"])
        runtime["refresh_battery_subscriptions"]()
        connection.send_result(
            msg["id"], {"updated": True, "device_id": msg["device_id"]}
        )

    for handler in (
        ws_get_data,
        ws_import_preview,
        ws_import_apply,
        ws_track_device,
        ws_dismiss_candidate,
        ws_update_settings,
        ws_add_model,
        ws_update_battery,
    ):
        websocket_api.async_register_command(hass, handler)


def _require_admin(connection: ActiveConnection) -> None:
    """Require an authenticated administrator for the management panel API."""
    if connection.user is None or not connection.user.is_admin:
        raise Unauthorized


def _get_runtime(hass: HomeAssistant) -> dict[str, Any]:
    """Return the one active global integration entry."""
    entries = hass.data.get(DOMAIN, {})
    if not entries:
        raise vol.Invalid("Strážca senzorov nie je načítaný")
    return next(iter(entries.values()))


def _add_device_entities(
    hass: HomeAssistant, runtime: dict[str, Any], device: dict[str, Any]
) -> None:
    """Create the minimal automation entities for a newly tracked device."""
    device_id = device["device_id"]
    group = runtime["entities"].setdefault(device_id, [])
    from .binary_sensor import GuardianBatteryAttention, GuardianProblem
    from .sensor import GuardianStatus

    add_binary = runtime["add_entities"].get("binary_sensor")
    add_sensor = runtime["add_entities"].get("sensor")
    if add_binary is None or add_sensor is None:
        raise vol.Invalid("The Home Assistant entity platforms are not ready")
    binary_entities = [GuardianProblem(hass, device, group)]
    if (
        device.get("tracking_mode") in {"battery_and_availability", "battery_only"}
        and device.get("power_type") != "mains"
    ):
        binary_entities.append(GuardianBatteryAttention(hass, device, group))
    add_binary(binary_entities)
    add_sensor([GuardianStatus(hass, device, group)])


async def _read_battery_notes_source(hass: HomeAssistant):
    """Read the migration source status for a concise preview notice."""
    from .migration.battery_notes import async_read_battery_notes

    return await async_read_battery_notes(hass)
