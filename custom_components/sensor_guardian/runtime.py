"""Runtime health evaluation, incident orchestration and transition events."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, callback

from .availability.engine import evaluate_health
from .diagnosis.dependencies import build_dependencies, correlated_clusters
from .diagnosis.incidents import close_incident, open_or_update_incident
from .diagnosis.scoring import classify_cause, score_evidence
from .events import (
    INCIDENT_EVENT,
    RECOVERED_EVENT,
    fire_event,
)


def _merge_data(runtime: dict[str, Any], updated: dict[str, Any]) -> None:
    """Keep root and device record identities stable for entities/listeners."""
    data = runtime["data"]
    current_devices = {item["device_id"]: item for item in data["devices"]}
    reconciled = []
    for record in updated["devices"]:
        existing = current_devices.get(record["device_id"])
        if existing is None:
            existing = {}
        existing.clear()
        existing.update(record)
        reconciled.append(existing)
    data["devices"][:] = reconciled
    for key, value in updated.items():
        if key == "devices":
            continue
        if isinstance(data.get(key), list) and isinstance(value, list):
            data[key][:] = value
        elif isinstance(data.get(key), dict) and isinstance(value, dict):
            data[key].clear()
            data[key].update(value)
        else:
            data[key] = value


def _evidence_for_device(
    hass: HomeAssistant, device: dict[str, Any]
) -> list[dict[str, Any]]:
    """Collect selected current values only; avoid copying source attributes."""
    evidence: list[dict[str, Any]] = []
    refs = device.get("entity_refs", {})
    if isinstance(refs, dict):
        level_entity = refs.get("battery_level")
        if isinstance(level_entity, str) and (state := hass.states.get(level_entity)):
            try:
                level = float(state.state)
            except ValueError:
                level = None
            if level is not None:
                evidence.append({"feature": "battery_level", "value": level})
        low_entity = refs.get("battery_low")
        if isinstance(low_entity, str) and (state := hass.states.get(low_entity)):
            evidence.append(
                {"feature": "native_battery_low", "value": state.state == "on"}
            )
    for signal in device.get("signal", []):
        if not isinstance(signal, dict) or not isinstance(signal.get("entity_id"), str):
            continue
        state = hass.states.get(signal["entity_id"])
        if state is None:
            continue
        try:
            value = float(state.state)
        except ValueError:
            continue
        kind = str(signal.get("kind", "")).casefold()
        if "rssi" in kind:
            evidence.append({"feature": "rssi_dbm", "value": value})
        elif kind in {"lqi", "linkquality"}:
            evidence.append({"feature": "linkquality", "value": value})
    estimate = device.get("battery_estimate", {})
    if isinstance(estimate, dict) and estimate.get("abnormal_drain") is True:
        evidence.append({"feature": "abnormal_drain", "value": True})
    entry_id = device.get("config_entry_id")
    if (
        isinstance(entry_id, str)
        and (source_entry := hass.config_entries.async_get_entry(entry_id))
        and source_entry.state is not ConfigEntryState.LOADED
    ):
        evidence.append({"feature": "source_entry_unavailable", "value": True})
    return evidence


def _active_incident(
    data: dict[str, Any], device_ids: list[str]
) -> dict[str, Any] | None:
    wanted = set(device_ids)
    return next(
        (
            incident
            for incident in data["incidents"]
            if set(incident.get("device_ids", [])) == wanted
            and not incident.get("closed_at")
        ),
        None,
    )


def _write_entities(runtime: dict[str, Any], device_id: str) -> None:
    for entity in runtime.get("entities", {}).get(device_id, []):
        if entity.hass is not None and entity.entity_id:
            entity.async_write_ha_state()


def _source_availability(hass: HomeAssistant, device: dict[str, Any]) -> bool | None:
    """HA source availability, not an assertion about a new radio packet."""
    ids = list(device.get("sentinels", []))
    refs = device.get("entity_refs", {})
    ids.extend(value for value in refs.values() if isinstance(value, str))
    states = [state for entity_id in set(ids) if (state := hass.states.get(entity_id))]
    if any(state.state not in {"unknown", "unavailable"} for state in states):
        return True
    if states and all(state.state == "unavailable" for state in states):
        return False
    return None


def _native_availability(hass: HomeAssistant, device: dict[str, Any]) -> bool | None:
    entity_id = device.get("entity_refs", {}).get("native_availability")
    if not entity_id:
        return device.get("native_available")
    state = hass.states.get(entity_id)
    if state is None or state.state == "unknown":
        return None
    return (
        True
        if state.state == "on"
        else False
        if state.state in {"off", "unavailable"}
        else None
    )


@callback
def schedule_device_processing(hass: HomeAssistant, runtime: dict[str, Any]) -> None:
    """Coalesce a burst of selected-entity writes into one runtime worker."""
    if runtime.get("stopping") or not runtime.get("ready", True):
        return
    runtime["_process_pending"] = True
    previous = runtime.get("_process_task")
    if previous is not None and not previous.done():
        return

    async def process_pending() -> None:
        while runtime.pop("_process_pending", False):
            await async_process_devices(hass, runtime)

    runtime["_process_task"] = hass.async_create_task(process_pending())


async def async_process_devices(
    hass: HomeAssistant,
    runtime: dict[str, Any],
    *,
    now: datetime | None = None,
) -> None:
    """Evaluate every tracked device, persist transitions and deduplicate events."""
    current = now or datetime.now(UTC)
    if runtime.get("stopping"):
        return
    data = runtime["data"]
    changed_ids: set[str] = set()
    for device in data["devices"]:
        if device.get("tracking_mode") == "ignored":
            continue
        previous = device.get("health_state", "unknown")
        profile = next(
            (
                item
                for item in data["availability_profiles"]
                if item["device_id"] == device["device_id"]
            ),
            {},
        )
        health = evaluate_health(
            now=current,
            startup_at=runtime["startup_at"],
            last_reported=device.get("last_reported_at"),
            profile=profile,
            native_available=_native_availability(hass, device),
            source_available=_source_availability(hass, device),
            previous_state=previous,
            recovery_started_at=device.get("recovery_started_at"),
            startup_grace=timedelta(
                minutes=float(data.get("settings", {}).get("startup_grace_minutes", 5))
            ),
            recovery_stability=timedelta(
                minutes=float(
                    data.get("settings", {}).get("recovery_stability_minutes", 2)
                )
            ),
        )
        if device.get("tracking_mode") == "battery_only":
            health = {"state": "not_monitored", "reason": "battery_only_mode"}
        new_state = health["state"]
        if new_state == "recovering" and not device.get("recovery_started_at"):
            device["recovery_started_at"] = current.isoformat()
        if new_state == "healthy":
            device["recovery_started_at"] = None
        if new_state != previous or device.get("health_reason") != health["reason"]:
            device["health_state"] = new_state
            device["health_reason"] = health["reason"]
            if new_state != previous:
                device["health_since"] = current.isoformat()
            changed_ids.add(device["device_id"])

    dependencies = build_dependencies(data["devices"])
    offline = [
        {
            "device_id": device["device_id"],
            "opened_at": device.get("health_since") or current.isoformat(),
        }
        for device in data["devices"]
        if device.get("health_state") == "offline"
    ]
    clusters = correlated_clusters(offline, dependencies)
    grouped_ids = {
        device_id for cluster in clusters for device_id in cluster["device_ids"]
    }
    new_single_incidents: list[tuple[str, str]] = []
    recovery_events: list[tuple[str, str]] = []
    for device in data["devices"]:
        device_id = device["device_id"]
        state = device.get("health_state", "unknown")
        evidence = _evidence_for_device(hass, device)
        scoring = score_evidence(evidence)
        cause_result = classify_cause(scoring)
        device["cause"] = cause_result["cause"]
        device["cause_confidence"] = cause_result["confidence"]
        if state in {"degraded", "stale", "offline"}:
            existing = _active_incident(data, [device_id])
            updated, incident = open_or_update_incident(
                data,
                device_ids=[device_id],
                now=current,
                health_state=state,
                cause_result=cause_result,
                evidence=evidence,
            )
            _merge_data(runtime, updated)
            data = runtime["data"]
            device = next(
                item for item in data["devices"] if item["device_id"] == device_id
            )
            active_ids = device.setdefault("active_incident_ids", [])
            if incident["incident_id"] not in active_ids:
                active_ids.append(incident["incident_id"])
            if existing is None or incident.get("notification_state") in {
                "pending",
                "snoozed",
            }:
                new_single_incidents.append((device_id, incident["incident_id"]))
            changed_ids.add(device_id)
        elif state == "healthy":
            incident = _active_incident(data, [device_id])
            if incident is not None:
                was_notified = incident.get("notification_state") == "sent"
                closed = close_incident(incident, now=current)
                incident.clear()
                incident.update(closed)
                device["active_incident_ids"] = [
                    item
                    for item in device.get("active_incident_ids", [])
                    if item != incident["incident_id"]
                ]
                if was_notified:
                    recovery_events.append((device_id, incident["incident_id"]))
                changed_ids.add(device_id)

    parent_incidents: list[tuple[str, list[str]]] = []
    for cluster in clusters:
        ids = cluster["device_ids"]
        existing = _active_incident(data, ids)
        evidence = [{"feature": "shared_outage_count", "value": len(ids)}]
        cause = classify_cause(score_evidence(evidence))
        updated, incident = open_or_update_incident(
            data,
            device_ids=ids,
            now=current,
            health_state="offline",
            cause_result=cause,
            evidence=evidence,
            dependency_id=cluster["dependency_id"],
        )
        _merge_data(runtime, updated)
        data = runtime["data"]
        for device_id in ids:
            device = next(
                item for item in data["devices"] if item["device_id"] == device_id
            )
            device["parent_incident_id"] = incident["incident_id"]
            for child in data["incidents"]:
                if child.get("device_ids") == [device_id] and not child.get(
                    "closed_at"
                ):
                    child["parent_incident_id"] = incident["incident_id"]
            changed_ids.add(device_id)
        if existing is None or incident.get("notification_state") in {
            "pending",
            "snoozed",
        }:
            parent_incidents.append((incident["incident_id"], ids))

    active_parent_ids = {cluster["dependency_id"] for cluster in clusters}
    for incident in data["incidents"]:
        if len(incident.get("device_ids", [])) < 3 or incident.get("closed_at"):
            continue
        if incident.get("dependency_id") not in active_parent_ids:
            was_notified = incident.get("notification_state") == "sent"
            closed = close_incident(incident, now=current)
            incident.clear()
            incident.update(closed)
            for device_id in incident["device_ids"]:
                device = next(
                    (
                        item
                        for item in data["devices"]
                        if item["device_id"] == device_id
                    ),
                    None,
                )
                if device is not None:
                    device["parent_incident_id"] = None
                for child in data["incidents"]:
                    if child.get("device_ids") == [device_id] and not child.get(
                        "closed_at"
                    ):
                        child["parent_incident_id"] = None
            if was_notified:
                recovery_events.append(
                    (incident["device_ids"][0], incident["incident_id"])
                )

    pending_events: list[tuple[str, str, list[str] | None]] = []
    for device_id, incident_id in new_single_incidents:
        incident = next(
            item for item in data["incidents"] if item["incident_id"] == incident_id
        )
        device = next(
            item for item in data["devices"] if item["device_id"] == device_id
        )
        if device_id in grouped_ids:
            incident["notification_state"] = "grouped"
            continue
        if _snoozed(device, current):
            incident["notification_state"] = "snoozed"
            continue
        incident["notification_state"] = "sent"
        pending_events.append((device_id, incident_id, None))
    for incident_id, ids in parent_incidents:
        incident = next(
            item for item in data["incidents"] if item["incident_id"] == incident_id
        )
        device = next(item for item in data["devices"] if item["device_id"] == ids[0])
        if _snoozed(device, current):
            incident["notification_state"] = "snoozed"
            continue
        incident["notification_state"] = "sent"
        pending_events.append((ids[0], incident_id, ids))
    for device_id in changed_ids:
        _write_entities(runtime, device_id)
    if changed_ids:
        await runtime["storage"].async_save(runtime["data"])
    for device_id, incident_id, affected_ids in pending_events:
        device = next(
            item
            for item in runtime["data"]["devices"]
            if item["device_id"] == device_id
        )
        incident = next(
            item
            for item in runtime["data"]["incidents"]
            if item["incident_id"] == incident_id
        )
        fire_event(
            hass, INCIDENT_EVENT, device, incident=incident, device_ids=affected_ids
        )
    for device_id, incident_id in recovery_events:
        device = next(
            item
            for item in runtime["data"]["devices"]
            if item["device_id"] == device_id
        )
        incident = next(
            item
            for item in runtime["data"]["incidents"]
            if item["incident_id"] == incident_id
        )
        fire_event(hass, RECOVERED_EVENT, device, incident=incident)


def _snoozed(device: dict[str, Any], now: datetime) -> bool:
    value = device.get("snoozed_until")
    if not isinstance(value, str):
        return False
    try:
        until = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    if until.tzinfo is None:
        until = until.replace(tzinfo=UTC)
    return until > now
