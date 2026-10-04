"""Explainable, read-only device discovery."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from types import SimpleNamespace
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry, entity_registry


@dataclass(frozen=True)
class DiscoveryCandidate:
    """A proposed tracking choice with reviewable supporting evidence."""

    device_id: str
    entity_refs: dict[str, str | None]
    signal_entities: tuple[str, ...]
    recommended_signal_entities: tuple[str, ...]
    suggested_mode: str
    confidence: str
    reasons: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-friendly candidate."""
        result = asdict(self)
        for key in ("signal_entities", "recommended_signal_entities", "reasons"):
            result[key] = list(result[key])
        return result


def _kind(entity: Any) -> str | None:
    """Classify an entity conservatively from registry metadata."""
    domain = entity.domain
    text = f"{entity.entity_id} {entity.original_name or ''} {entity.unique_id}".lower()
    device_class = getattr(entity, "device_class", None)
    unit = (getattr(entity, "unit_of_measurement", None) or "").lower()
    if "battery" in text and (domain == "binary_sensor" or device_class == "battery"):
        return "battery_low"
    if "battery" in text and domain == "sensor" and unit in {"%", "percent"}:
        return "battery_level"
    if "voltage" in text or unit in {"v", "mv"}:
        return "voltage"
    if (
        any(token in text for token in ("rssi", "lqi", "linkquality", "signal"))
        or device_class == "signal_strength"
    ):
        return "signal"
    if domain == "binary_sensor" and (
        device_class == "connectivity"
        or any(token in text for token in ("availability", "online", "connectivity"))
    ):
        return "native_availability"
    return None


def rank_device_entities(
    device_id: str, entities: list[Any]
) -> DiscoveryCandidate | None:
    """Rank useful entities; signal recommendations never enable entities."""
    refs: dict[str, str | None] = {
        key: None
        for key in ("battery_level", "battery_low", "voltage", "native_availability")
    }
    signals: list[str] = []
    recommended: list[str] = []
    reasons: list[str] = []
    sentinel_ids: list[str] = []
    for entity in entities:
        kind = _kind(entity)
        if kind is None:
            continue
        if kind == "signal":
            sentinel_ids.append(entity.entity_id)
            (recommended if getattr(entity, "disabled_by", None) else signals).append(
                entity.entity_id
            )
            continue
        if getattr(entity, "disabled_by", None):
            continue
        if refs[kind] is None:
            refs[kind] = entity.entity_id
        sentinel_ids.append(entity.entity_id)
    has_battery = any(refs[key] for key in ("battery_level", "battery_low", "voltage"))
    has_availability = refs["native_availability"] is not None or bool(signals)
    if has_battery and has_availability:
        mode, confidence = "battery_and_availability", "high"
    elif has_battery:
        mode, confidence = "battery_only", "medium"
    elif has_availability:
        mode, confidence = "availability_only", "medium"
    else:
        return None
    reasons.extend(
        f"enabled {label} entity"
        for key, label in (
            ("battery_level", "battery percentage"),
            ("battery_low", "native battery-low"),
            ("voltage", "voltage"),
            ("native_availability", "connectivity"),
        )
        if refs[key]
    )
    if signals:
        reasons.append("enabled signal-quality entity available")
    if recommended:
        reasons.append("disabled signal-quality entities could improve diagnostics")
    return DiscoveryCandidate(
        device_id,
        refs,
        tuple(signals),
        tuple(recommended),
        mode,
        confidence,
        tuple(reasons),
    )


async def async_discover_devices(
    hass: HomeAssistant,
    *,
    tracked_device_ids: set[str] | None = None,
    dismissed_device_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Return untracked candidates without changing registry or entity states."""
    tracked, dismissed = tracked_device_ids or set(), dismissed_device_ids or set()
    devices, entities = device_registry.async_get(hass), entity_registry.async_get(hass)
    by_device: dict[str, list[Any]] = {}
    for entity in entities.entities.values():
        if entity.device_id:
            state = hass.states.get(entity.entity_id)
            attributes = state.attributes if state is not None else {}
            by_device.setdefault(entity.device_id, []).append(
                SimpleNamespace(
                    entity_id=entity.entity_id,
                    domain=entity.domain,
                    original_name=entity.original_name,
                    unique_id=entity.unique_id,
                    disabled_by=entity.disabled_by,
                    device_class=(
                        getattr(entity, "original_device_class", None)
                        or attributes.get("device_class")
                    ),
                    unit_of_measurement=attributes.get("unit_of_measurement"),
                )
            )
    result: list[dict[str, Any]] = []
    for device in devices.devices:
        if device.id in tracked or device.id in dismissed:
            continue
        matching = by_device.get(device.id, [])
        candidate = rank_device_entities(device.id, matching)
        if candidate is not None:
            result.append(candidate.as_dict())
    return result
