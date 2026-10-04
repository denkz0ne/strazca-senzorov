"""One-time, idempotent Battery Notes import with provenance and backup."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from homeassistant.components.recorder import history, statistics
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry
from homeassistant.helpers.storage import Store

from ..models import (
    GuardianData,
    StorageDataError,
    validate_store_data,
)

BATTERY_NOTES_DOMAIN = "battery_notes"
BATTERY_NOTES_STORAGE_KEY = "battery_notes.storage"
BATTERY_NOTES_STORAGE_VERSION = 1


def _stable_id(prefix: str, value: object) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), default=str
    ).encode()
    return f"{prefix}_{hashlib.sha256(encoded).hexdigest()[:20]}"


def convert_battery_notes_library(
    source: dict[str, Any], source_commit: str
) -> dict[str, Any]:
    """Convert one pinned upstream catalogue snapshot to our bundled format."""
    if not isinstance(source.get("devices"), list):
        raise StorageDataError("Battery Notes catalogue must contain a devices list")
    records: dict[str, dict[str, Any]] = {}
    for item in source["devices"]:
        if (
            not isinstance(item, dict)
            or not isinstance(item.get("model"), str)
            or not isinstance(item.get("battery_type"), str)
        ):
            continue
        semantic = {
            key: item.get(key)
            for key in (
                "manufacturer",
                "model",
                "model_id",
                "hw_version",
                "battery_type",
                "battery_quantity",
                "model_match_method",
            )
        }
        record: dict[str, Any] = {
            "model_id": _stable_id("bn", semantic),
            "manufacturer": item.get("manufacturer"),
            "model": item["model"],
            "model_ids": [item["model_id"]] if item.get("model_id") else [],
            "hardware_versions": [item["hw_version"]] if item.get("hw_version") else [],
            "default_battery_type": item["battery_type"],
            "default_battery_quantity": item.get("battery_quantity", 1),
            "power_hint": _power_hint(item["battery_type"]),
            "replaceable": _replaceable(item["battery_type"]),
            "source": "imported",
            "source_attribution": (
                "Battery Notes library (MIT), converted from pinned snapshot"
            ),
        }
        method = item.get("model_match_method")
        if method:
            record["match_rules"] = [
                {"field": "model", "value": item["model"], "match_type": method}
            ]
        records[record["model_id"]] = record
    return {
        "schema_version": 1,
        "source": {
            "name": "Battery Notes",
            "repository": "https://github.com/andrew-codechimp/HA-Battery-Notes",
            "commit": source_commit,
            "file": "library/library.json",
            "upstream_schema_version": source.get("version"),
            "license": "MIT; see BATTERY_NOTES_LICENSE.txt",
        },
        "ignored_domains": source.get("ignored_domains", []),
        "models": list(records.values()),
    }


def _power_hint(battery_type: str) -> str:
    value = battery_type.casefold()
    if (
        "recharge" in value
        or value.startswith("lir")
        or "18650" in value
        or "li-ion" in value
        or "lifepo" in value
    ):
        return "rechargeable"
    if value in {"solar", "irreplaceable", "sealed 10-year", "manual"}:
        return "unknown"
    return "replaceable_battery"


def _replaceable(battery_type: str) -> bool | None:
    hint = _power_hint(battery_type)
    return (
        True
        if hint == "replaceable_battery"
        else False
        if battery_type.casefold() in {"irreplaceable", "sealed 10-year", "solar"}
        else None
    )


def _parse_datetime(value: Any) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).isoformat()
    except ValueError:
        # Older Battery Notes releases serialized microseconds after a colon.
        head, colon, tail = value.rpartition(":")
        if colon and tail[:6].isdigit():
            try:
                return datetime.fromisoformat(
                    f"{head}.{tail[:6]}{tail[6:]}".replace("Z", "+00:00")
                ).isoformat()
            except ValueError:
                pass
    return None


def _state_get(state: Any, key: str, default: Any = None) -> Any:
    """Read a field from a Recorder State or minimal response mapping."""
    return (
        state.get(key, default)
        if isinstance(state, dict)
        else getattr(state, key, default)
    )


def build_import_preview(
    *,
    source_store: object,
    source_entries: list[dict[str, Any]],
    device_ids: set[str],
    entity_to_device: dict[str, str],
    existing_data: dict[str, Any],
    catalogue_count: int,
    recorder_history: dict[str, list[Any]] | None = None,
    recorder_statistics: dict[str, list[Any]] | None = None,
) -> dict[str, Any]:
    """Build a deterministic proposal. Does not mutate source or target data."""
    if source_store is not None and not isinstance(source_store, dict):
        raise StorageDataError("Battery Notes storage must be an object")
    stored = source_store if isinstance(source_store, dict) else {}
    device_values = stored.get("devices", [])
    entity_values = stored.get("entities", [])
    if not isinstance(device_values, list) or not isinstance(entity_values, list):
        raise StorageDataError("Battery Notes device/entity state must be lists")
    current = validate_store_data(existing_data)
    updates: dict[str, dict[str, Any]] = {}
    unmatched: list[dict[str, Any]] = []
    sources = [
        (item, item.get("device_id"))
        for item in device_values
        if isinstance(item, dict)
    ]
    for item in entity_values:
        if isinstance(item, dict):
            sources.append((item, entity_to_device.get(item.get("entity_id", ""))))
    for entry in source_entries:
        data = entry.get("data", {}) if isinstance(entry, dict) else {}
        if not isinstance(data, dict) or not any(
            key in data
            for key in (
                "battery_type",
                "battery_quantity",
                "device_id",
                "source_entity_id",
            )
        ):
            continue
        device_id = data.get("device_id") or entity_to_device.get(
            data.get("source_entity_id", "")
        )
        if device_id:
            updates.setdefault(device_id, {}).update(
                {
                    key: data[key]
                    for key in ("battery_type", "battery_quantity")
                    if key in data
                }
            )
    existing = {item["device_id"]: item for item in current["devices"]}
    cycles: list[dict[str, Any]] = []
    samples: list[dict[str, Any]] = []
    for item, device_id in sources:
        if not device_id or device_id not in device_ids:
            unmatched.append({"source": deepcopy(item), "device_id": device_id})
            continue
        proposal = updates.setdefault(device_id, {})
        replaced = _parse_datetime(item.get("battery_last_replaced"))
        reported = _parse_datetime(item.get("battery_last_reported"))
        level = item.get("battery_last_reported_level")
        if replaced and "battery_last_replaced" not in proposal:
            proposal["battery_last_replaced"] = replaced
        if level is not None and reported:
            samples.append(
                {
                    "sample_id": _stable_id("bn_sample", [device_id, reported, level]),
                    "device_id": device_id,
                    "timestamp": reported,
                    "level_percent": level,
                    "provenance": "battery_notes_explicit",
                }
            )
        if replaced:
            cycle_id = _stable_id("bn_cycle", [device_id, replaced])
            cycles.append(
                {
                    "cycle_id": cycle_id,
                    "device_id": device_id,
                    "started_at": replaced,
                    "battery_type": proposal.get("battery_type"),
                    "battery_quantity": proposal.get("battery_quantity", 1),
                    "provenance": "battery_notes_explicit",
                }
            )
    for entity_id, states in (recorder_history or {}).items():
        device_id = entity_to_device.get(entity_id)
        if device_id not in device_ids:
            continue
        for state in states[-500:]:
            try:
                level = float(_state_get(state, "state"))
            except TypeError, ValueError:
                continue
            timestamp = _state_get(state, "last_updated") or _state_get(
                state, "last_changed"
            )
            timestamp = (
                _parse_datetime(timestamp)
                if isinstance(timestamp, str)
                else timestamp.isoformat()
                if isinstance(timestamp, datetime)
                else None
            )
            if timestamp and 0 <= level <= 100:
                samples.append(
                    {
                        "sample_id": _stable_id(
                            "recorder", [device_id, timestamp, level]
                        ),
                        "device_id": device_id,
                        "timestamp": timestamp,
                        "level_percent": level,
                        "source_entity_ids": [entity_id],
                        "provenance": "recorder_exact",
                    }
                )
    for entity_id, points in (recorder_statistics or {}).items():
        device_id = entity_to_device.get(entity_id)
        if device_id not in device_ids:
            continue
        for point in points[-500:]:
            if not isinstance(point, dict):
                point = {
                    key: getattr(point, key, None) for key in ("start", "mean", "state")
                }
            level = point.get("mean", point.get("state"))
            try:
                level = float(level)
            except TypeError, ValueError:
                continue
            timestamp = point.get("start")
            timestamp = (
                _parse_datetime(timestamp)
                if isinstance(timestamp, str)
                else timestamp.isoformat()
                if isinstance(timestamp, datetime)
                else None
            )
            if timestamp and 0 <= level <= 100:
                samples.append(
                    {
                        "sample_id": _stable_id(
                            "statistics", [device_id, timestamp, level]
                        ),
                        "device_id": device_id,
                        "timestamp": timestamp,
                        "level_percent": level,
                        "source_entity_ids": [entity_id],
                        "quality_flags": ["aggregated_statistics"],
                        "provenance": "statistics_inferred",
                    }
                )
    for device_id, proposal in updates.items():
        if device_id in existing:
            for key in ("battery_type", "battery_quantity"):
                proposal.pop(key, None)
    return {
        "source": "battery_notes",
        "catalogue_model_count": catalogue_count,
        "matched_device_count": len(updates),
        "unmatched_count": len(unmatched),
        "updates": updates,
        "unmatched": unmatched,
        "cycles": cycles,
        "samples": samples,
        "history_note": (
            "Recorder exact states and aggregated long-term statistics "
            "retain separate provenance."
        ),
        "receipt_id": _stable_id("import", [updates, cycles, samples, unmatched]),
    }


def apply_import_preview(
    data: dict[str, Any], preview: dict[str, Any]
) -> tuple[GuardianData, dict[str, Any]]:
    """Apply reviewed proposals once, preserving overrides and unmatched rows."""
    result = validate_store_data(data)
    backup = {"version": 1, "minor_version": 1, "data": deepcopy(result)}
    settings = result["settings"]
    receipts = settings.setdefault("migration_receipts", {})
    if not isinstance(receipts, dict):
        raise StorageDataError("migration_receipts setting must be an object")
    receipt_id = preview.get("receipt_id")
    if not isinstance(receipt_id, str) or not receipt_id:
        raise StorageDataError("Import preview requires a receipt ID")
    if receipt_id in receipts:
        return result, backup
    devices = {item["device_id"]: item for item in result["devices"]}
    for device_id, proposal in preview.get("updates", {}).items():
        record = devices.get(device_id)
        if record is None:
            record = {"device_id": device_id}
            result["devices"].append(record)
            devices[device_id] = record
        for key, value in proposal.items():
            if key not in record and key not in record.get("user_overrides", {}):
                record[key] = value
    for collection in ("cycles", "samples"):
        identifiers = {
            item["cycle_id" if collection == "cycles" else "sample_id"]
            for item in result[collection]
        }
        id_key = "cycle_id" if collection == "cycles" else "sample_id"
        for proposed in preview.get(collection, []):
            if proposed.get(id_key) not in identifiers:
                result[collection].append(deepcopy(proposed))
                identifiers.add(proposed[id_key])
    if preview.get("unmatched"):
        settings.setdefault("unmatched_import_records", []).extend(
            deepcopy(preview["unmatched"])
        )
    receipts[receipt_id] = {
        "source": "battery_notes",
        "imported_at": datetime.now().astimezone().isoformat(),
    }
    return validate_store_data(result), backup


def restore_backup(backup: object) -> GuardianData:
    """Validate a versioned export before a caller replaces persistent data."""
    if (
        not isinstance(backup, dict)
        or backup.get("version") != 1
        or not isinstance(backup.get("data"), dict)
    ):
        raise StorageDataError("Unsupported Sensor Guardian backup")
    return validate_store_data(backup["data"])


async def async_read_battery_notes(
    hass: HomeAssistant,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """Read existing Battery Notes storage and config entries once, if installed."""
    store = Store(
        hass, BATTERY_NOTES_STORAGE_VERSION, BATTERY_NOTES_STORAGE_KEY, minor_version=2
    )
    raw = await store.async_load()
    entries: list[dict[str, Any]] = []
    for entry in hass.config_entries.async_entries(BATTERY_NOTES_DOMAIN):
        entries.append({"data": dict(entry.data), "title": entry.title})
        for subentry in getattr(entry, "subentries", {}).values():
            entries.append({"data": dict(subentry.data), "title": subentry.title})
    return raw if isinstance(raw, dict) else None, entries


async def async_read_recorder_history(
    hass: HomeAssistant, entity_to_device: dict[str, str], *, days: int = 365
) -> tuple[dict[str, list[Any]], dict[str, list[Any]]]:
    """Read a bounded history window for selected Battery Notes entities only."""
    if not 1 <= days <= 3650:
        raise ValueError("Recorder history window must be between 1 and 3650 days")
    if not entity_to_device:
        return {}, {}
    end = datetime.now(UTC)
    start = end - timedelta(days=days)
    entity_ids = sorted(entity_to_device)
    history_result = await hass.async_add_executor_job(
        history.get_significant_states,
        hass,
        start,
        end,
        entity_ids,
        None,
        True,
        False,
        True,
        True,
        False,
    )
    metadata = await hass.async_add_executor_job(
        statistics.get_metadata, hass, statistic_ids=set(entity_ids)
    )
    statistic_ids = set(metadata)
    stats_result = {}
    if statistic_ids:
        stats_result = await hass.async_add_executor_job(
            statistics.statistics_during_period,
            hass,
            start,
            end,
            statistic_ids,
            "day",
            None,
            {"mean", "state"},
        )
    return history_result, stats_result


async def async_build_import_preview(
    hass: HomeAssistant,
    *,
    existing_data: dict[str, Any],
    device_ids: set[str],
    days: int = 365,
) -> dict[str, Any]:
    """Collect available Battery Notes inputs and build the user-reviewable proposal."""
    source_store, entries = await async_read_battery_notes(hass)
    registry = entity_registry.async_get(hass)
    entity_to_device: dict[str, str] = {}
    entity_ids: set[str] = set()
    for item in (
        source_store.get("entities", []) if isinstance(source_store, dict) else []
    ):
        if isinstance(item, dict) and isinstance(item.get("entity_id"), str):
            entity_ids.add(item["entity_id"])
    for entry in entries:
        source_entity = entry.get("data", {}).get("source_entity_id")
        if isinstance(source_entity, str):
            entity_ids.add(source_entity)
    for entity_id in entity_ids:
        registry_entry = registry.async_get(entity_id)
        if registry_entry and registry_entry.device_id:
            entity_to_device[entity_id] = registry_entry.device_id
    history_data, statistics_data = await async_read_recorder_history(
        hass, entity_to_device, days=days
    )
    catalogue_path = Path(__file__).parents[1] / "data" / "battery_models.json"
    try:
        catalogue = json.loads(catalogue_path.read_text(encoding="utf-8"))
        catalogue_count = len(catalogue.get("models", []))
    except OSError, ValueError, TypeError:
        catalogue_count = 0
    return build_import_preview(
        source_store=source_store,
        source_entries=entries,
        device_ids=device_ids,
        entity_to_device=entity_to_device,
        existing_data=existing_data,
        catalogue_count=catalogue_count,
        recorder_history=history_data,
        recorder_statistics=statistics_data,
    )


async def async_apply_import_preview(
    storage: Any, data: dict[str, Any], preview: dict[str, Any]
) -> tuple[GuardianData, dict[str, Any]]:
    """Apply an explicitly reviewed preview; return a pre-import backup envelope."""
    updated, backup = apply_import_preview(data, preview)
    if preview.get("receipt_id") in updated["settings"].get("migration_receipts", {}):
        await storage.async_save(updated)
    return updated, backup
