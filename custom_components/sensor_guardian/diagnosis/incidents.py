"""Deduplicated incident lifecycle and auditable cause revisions."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from ..history import stable_id
from ..models import GuardianData, validate_store_data


def open_or_update_incident(
    data: dict[str, Any],
    *,
    device_ids: list[str],
    now: datetime,
    health_state: str,
    cause_result: dict[str, Any],
    evidence: list[dict[str, Any]],
    dependency_id: str | None = None,
    parent_incident_id: str | None = None,
) -> tuple[GuardianData, dict[str, Any]]:
    """Update a matching active incident or open one deterministic incident."""
    result = validate_store_data(data)
    affected = sorted(set(device_ids))
    if not affected:
        raise ValueError("An incident must affect at least one device")
    existing = next(
        (
            item
            for item in result["incidents"]
            if not item.get("closed_at")
            and item.get("device_ids") == affected
            and item.get("kind", "availability") == "availability"
        ),
        None,
    )
    stamp = (
        now.astimezone(UTC).isoformat()
        if now.tzinfo
        else now.replace(tzinfo=UTC).isoformat()
    )
    if existing:
        existing["updated_at"] = stamp
        existing["health_state"] = health_state
        existing["evidence"] = deepcopy(evidence)
        existing["dependency_id"] = dependency_id or existing.get("dependency_id")
        existing["parent_incident_id"] = parent_incident_id or existing.get(
            "parent_incident_id"
        )
        revised, _ = revise_cause(
            existing, cause_result, evidence, now=now, provenance="inferred"
        )
        existing.update(revised)
        return result, deepcopy(existing)
    seed = json.dumps([affected, stamp], separators=(",", ":"))
    incident = {
        "incident_id": "incident_" + hashlib.sha256(seed.encode()).hexdigest()[:20],
        "device_ids": affected,
        "opened_at": stamp,
        "updated_at": stamp,
        "health_state": health_state,
        "cause": cause_result.get("cause", "unknown"),
        "confidence": cause_result.get("confidence", "none"),
        "severity": "warning",
        "evidence": deepcopy(evidence),
        "cause_history": [
            {
                "at": stamp,
                "cause": cause_result.get("cause", "unknown"),
                "confidence": cause_result.get("confidence", "none"),
                "provenance": "inferred",
                "reason_code": cause_result.get("reason_code"),
            }
        ],
        "parent_incident_id": parent_incident_id,
        "dependency_id": dependency_id,
        "acknowledged": False,
        "snoozed_until": None,
        "notification_state": "pending",
    }
    result["incidents"].append(incident)
    return result, deepcopy(incident)


def revise_cause(
    incident: dict[str, Any],
    cause_result: dict[str, Any],
    evidence: list[dict[str, Any]],
    *,
    now: datetime,
    provenance: str = "inferred",
) -> tuple[dict[str, Any], bool]:
    """Append a revision only if the label changes; retain prior evidence trail."""
    result = deepcopy(incident)
    new_cause = cause_result.get("cause", "unknown")
    changed = result.get("cause") != new_cause
    result["evidence"] = deepcopy(evidence)
    result["updated_at"] = (
        now.astimezone(UTC).isoformat()
        if now.tzinfo
        else now.replace(tzinfo=UTC).isoformat()
    )
    if provenance == "inferred" and result.get("confirmed_cause") not in {
        None,
        "unknown",
    }:
        result["cause"] = result["confirmed_cause"]
        result["confidence"] = "high"
        return result, False
    if changed:
        history = result.setdefault("cause_history", [])
        history.append(
            {
                "at": result["updated_at"],
                "cause": new_cause,
                "previous_cause": result.get("cause", "unknown"),
                "confidence": cause_result.get("confidence", "none"),
                "provenance": provenance,
                "reason_code": cause_result.get("reason_code"),
                "evidence": deepcopy(evidence),
            }
        )
        result["cause"] = new_cause
    result["confidence"] = cause_result.get("confidence", "none")
    if provenance == "user_confirmed":
        result["confirmed_cause"] = new_cause
    return result, changed


def close_incident(incident: dict[str, Any], *, now: datetime) -> dict[str, Any]:
    """Close an incident idempotently while preserving its history."""
    result = deepcopy(incident)
    if not result.get("closed_at"):
        result["closed_at"] = (
            now.astimezone(UTC).isoformat()
            if now.tzinfo
            else now.replace(tzinfo=UTC).isoformat()
        )
        result["updated_at"] = result["closed_at"]
        result["health_state"] = "healthy"
        result["notification_state"] = "recovered"
    return result


def sync_battery_alert(
    data: dict,
    device: dict,
    *,
    now: datetime,
    level=None,
    native_low=None,
    estimate=None,
) -> bool:
    """Battery attention is independent of device communication availability."""
    active = next(
        (
            row
            for row in data["incidents"]
            if row.get("kind") == "battery"
            and row["device_ids"] == [device["device_id"]]
            and not row.get("closed_at")
        ),
        None,
    )
    monitored = (
        device.get("tracking_mode") in {"battery_only", "battery_and_availability"}
        and device.get("power_type") != "mains"
    )
    if not monitored or not device.get("battery_attention"):
        if active:
            closed = close_incident(active, now=now)
            active.clear()
            active.update(closed)
            active["resolution"] = (
                "battery_attention_cleared" if monitored else "monitoring_disabled"
            )
        return False
    severity = (
        "critical"
        if native_low is True or (level is not None and level <= 5)
        else "warning"
    )
    fresh = active is None
    escalated = bool(
        active and active.get("severity") != "critical" and severity == "critical"
    )
    if fresh:
        active = {
            "incident_id": "battery_" + stable_id(device["device_id"], now.isoformat()),
            "kind": "battery",
            "device_ids": [device["device_id"]],
            "opened_at": now.isoformat(),
            "acknowledged": False,
            "notification_state": "pending",
            "cause": "battery",
            "confidence": "medium",
            "parent_incident_id": None,
        }
        data["incidents"].append(active)
    evidence = []
    if level is not None:
        evidence.append({"feature": "battery_level", "value": level})
    if native_low is not None:
        evidence.append({"feature": "native_battery_low", "value": native_low})
    if estimate and estimate.get("abnormal_drain"):
        evidence.append({"feature": "abnormal_drain", "value": True})
    active.update(
        updated_at=now.isoformat(),
        health_state="battery_attention",
        severity=severity,
        evidence=evidence,
    )
    if escalated:
        active["acknowledged"] = False
    return fresh or escalated
