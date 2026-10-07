"""Pure, explainable dashboard/detail/stock DTOs over stored evidence."""

from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from statistics import median

from .history import number, parse_time


def evidence_index(data: dict) -> dict:
    index = {
        key: defaultdict(list)
        for key in ("samples", "cycles", "signal_samples", "health_history")
    }
    for key in index:
        for row in data.get(key, []):
            index[key][row["device_id"]].append(row)
        for rows in index[key].values():
            rows.sort(key=lambda row: row.get("timestamp", row.get("started_at", "")))
    index["profiles"] = {
        row["device_id"]: row for row in data.get("availability_profiles", [])
    }
    return index


def signal_trend(rows: list, *, now: datetime) -> dict:
    for kind in ("rssi", "lqi", "linkquality"):
        points = [
            row
            for row in rows
            if row.get("kind") == kind
            and (stamp := parse_time(row.get("timestamp")))
            and now - stamp <= timedelta(days=30)
        ]
        if len(points) < 6:
            continue
        first, last = (
            parse_time(points[0]["timestamp"]),
            parse_time(points[-1]["timestamp"]),
        )
        if last - first < timedelta(days=1):
            continue
        change = median(row["value"] for row in points[-3:]) - median(
            row["value"] for row in points[:3]
        )
        if change <= (-10 if kind == "rssi" else -30):
            return {"state": "degrading", "kind": kind, "change": round(change, 1)}
    return {"state": "insufficient_history"}


def device_snapshot(
    data: dict,
    device: dict,
    *,
    now: datetime,
    index: dict | None = None,
    live: dict | None = None,
) -> dict:
    index = index or evidence_index(data)
    device_id = device["device_id"]
    samples, cycles = index["samples"][device_id], index["cycles"][device_id]
    observed = live or {}

    def reading(key, field):
        if field in observed:
            return observed[field]
        return next(
            (row[key] for row in reversed(samples) if row.get(key) is not None),
            device.get(field),
        )

    level = number(reading("level_percent", "battery_level"))
    voltage = number(reading("voltage", "voltage"))
    low = reading("native_low", "battery_low")
    mode = device.get("tracking_mode", "availability_only")
    powered = device.get("power_type", "unknown")
    battery = (
        mode in {"battery_only", "battery_and_availability"} and powered != "mains"
    )
    estimate = deepcopy(
        device.get("battery_estimate")
        or {
            "remaining_days_range": None,
            "confidence": "none",
            "reason_codes": ["no_valid_samples"],
        }
    )
    state = device.get("health_state", "unknown")
    missing = []
    if state in {"unknown", "initializing"}:
        missing.append("availability_learning")
    if battery and level is None and voltage is None and low is None:
        missing.append("battery_source_missing")
    if battery and not estimate.get("remaining_days_range"):
        missing.append("estimate_learning")
    if device.get("recommended_signal_entities"):
        missing.append("signal_disabled")
    trend = signal_trend(index["signal_samples"][device_id], now=now)
    rules = {**data.get("settings", {}), **device.get("rules", {})}
    span = 0.0
    if (
        len(samples) > 1
        and parse_time(samples[0]["timestamp"])
        and parse_time(samples[-1]["timestamp"])
    ):
        span = (
            parse_time(samples[-1]["timestamp"]) - parse_time(samples[0]["timestamp"])
        ).total_seconds() / 86400
    priority, risk, reasons, action = 4, "normal", [], "view"
    if mode == "ignored":
        priority, risk, action = 5, "paused", "resume"
    elif state == "offline":
        priority, risk, reasons, action = 0, "critical", ["device_offline"], "diagnose"
    elif state in {"degraded", "stale"}:
        priority, risk, reasons, action = (
            1,
            "attention",
            ["availability_degraded"],
            "diagnose",
        )
    elif battery and (
        low is True
        or (
            level is not None and level <= float(rules.get("low_battery_threshold", 20))
        )
        or estimate.get("abnormal_drain")
        or device.get("battery_attention")
    ):
        priority, risk, reasons, action = (
            1,
            "attention",
            ["rapid_drain" if estimate.get("abnormal_drain") else "battery_low"],
            "check_battery",
        )
    else:
        window = estimate.get("remaining_days_range")
        if (
            battery
            and window
            and estimate.get("confidence") != "none"
            and window["min"] <= int(rules.get("prevention_horizon_days", 14))
        ):
            priority, risk, reasons, action = (
                2,
                "watch",
                ["replacement_window"],
                "plan_replacement",
            )
        elif trend["state"] == "degrading":
            priority, risk, reasons, action = (
                2,
                "watch",
                ["signal_degrading"],
                "check_signal",
            )
        elif missing:
            priority, risk, reasons, action = (
                3,
                "learning",
                missing[:],
                "review_sources",
            )
    return {
        **{
            key: deepcopy(device.get(key))
            for key in (
                "device_id",
                "name",
                "area_id",
                "area_name",
                "source_integration",
                "transport",
                "tracking_mode",
                "power_type",
                "last_reported_at",
                "health_reason",
                "battery_type",
                "battery_quantity",
                "snoozed_until",
                "cause_confidence",
                "recommended_signal_entities",
                "history_status",
                "rules",
            )
        },
        "health_state": state,
        "cause": device.get("cause", "unknown"),
        "battery_level": level,
        "battery_low": low,
        "voltage": voltage,
        "signal_values": observed.get("signal_values", []),
        "last_replaced_at": cycles[-1].get("started_at") if cycles else None,
        "estimate": estimate,
        "sample_count": len(samples),
        "report_count": len(
            index["profiles"].get(device_id, {}).get("report_timestamps", [])
        ),
        "span_days": round(span, 1),
        "quality": {
            "state": "incomplete" if missing else "complete",
            "missing": missing,
        },
        "risk": {
            "level": risk,
            "priority": priority,
            "reasons": reasons,
            "action": action,
        },
        "signal_trend": trend,
    }


def alert_rows(data: dict, *, include_closed: bool = False) -> list:
    names = {
        row["device_id"]: row.get("name") or "Sledované zariadenie"
        for row in data.get("devices", [])
    }
    active = {
        row["incident_id"]
        for row in data.get("incidents", [])
        if not row.get("closed_at")
    }
    result = []
    for row in reversed(data.get("incidents", [])):
        if (not include_closed and row.get("closed_at")) or row.get(
            "parent_incident_id"
        ) in active:
            continue
        result.append(
            {
                **{
                    key: deepcopy(row.get(key))
                    for key in (
                        "incident_id",
                        "device_ids",
                        "opened_at",
                        "updated_at",
                        "closed_at",
                        "health_state",
                        "cause",
                        "cause_confidence",
                        "acknowledged",
                        "snoozed_until",
                        "resolution",
                    )
                },
                "device_count": len(set(row.get("device_ids", []))),
                "names": [
                    names.get(device_id, "Sledované zariadenie")
                    for device_id in row.get("device_ids", [])
                ],
                "evidence": [
                    {
                        key: point[key]
                        for key in ("feature", "value", "timestamp", "quality")
                        if key in point
                    }
                    for point in row.get("evidence", [])
                ],
            }
        )
    return result


def dashboard(
    data: dict, *, now: datetime | None = None, live: dict | None = None
) -> dict:
    now = now or datetime.now(UTC)
    index = evidence_index(data)
    rows = [
        device_snapshot(
            data,
            device,
            now=now,
            index=index,
            live=(live or {}).get(device["device_id"]),
        )
        for device in data.get("devices", [])
        if device.get("tracking_mode") != "ignored"
    ]
    counts = {
        "total": len(rows),
        "offline": sum(row["health_state"] == "offline" for row in rows),
        "attention": sum(row["risk"]["priority"] <= 1 for row in rows),
        "prevention": sum(row["risk"]["level"] == "watch" for row in rows),
        "coverage": sum(row["quality"]["state"] != "complete" for row in rows),
        "healthy": sum(row["health_state"] == "healthy" for row in rows),
    }
    ranked = sorted(
        rows, key=lambda row: (row["risk"]["priority"], (row["name"] or "").casefold())
    )
    return {
        "counts": counts,
        "devices": rows,
        "urgent": [row for row in ranked if row["risk"]["priority"] <= 1][:12],
        "prevention": [row for row in ranked if row["risk"]["level"] == "watch"][:12],
        "coverage": [row for row in ranked if row["quality"]["state"] != "complete"][
            :12
        ],
        "alerts": alert_rows(data)[:12],
        "recent": list(reversed(data.get("health_history", [])))[0:12],
        "observed_at": now.isoformat(),
    }


def device_detail(
    data: dict,
    device_id: str,
    *,
    days: int = 30,
    now: datetime | None = None,
    live: dict | None = None,
) -> dict:
    now = now or datetime.now(UTC)
    device = next(
        (row for row in data["devices"] if row["device_id"] == device_id), None
    )
    if device is None:
        raise ValueError("Device is not tracked")
    index, start = evidence_index(data), now - timedelta(days=days)

    def selected(key):
        return [
            row
            for row in index[key][device_id]
            if (stamp := parse_time(row.get("timestamp", row.get("started_at"))))
            and start <= stamp <= now
        ]

    history = selected("health_history")
    prior = [
        row
        for row in index["health_history"][device_id]
        if (stamp := parse_time(row["timestamp"])) and stamp < start
    ]
    if prior:
        history.insert(
            0,
            {
                **prior[-1],
                "timestamp": start.isoformat(),
                "provenance": "state_at_window_start",
            },
        )
    return {
        "device": device_snapshot(data, device, now=now, index=index, live=live),
        "series": {
            "battery": [
                {
                    "timestamp": row["timestamp"],
                    "value": row.get("level_percent"),
                    "provenance": row.get("provenance"),
                }
                for row in selected("samples")
            ],
            "voltage": [
                {"timestamp": row["timestamp"], "value": row.get("voltage")}
                for row in selected("samples")
                if row.get("voltage") is not None
            ],
            "signal": [
                {
                    "timestamp": row["timestamp"],
                    "value": row["value"],
                    "kind": row["kind"],
                    "resolution": row.get("resolution"),
                }
                for row in selected("signal_samples")
            ],
            "availability": [
                {
                    "timestamp": row["timestamp"],
                    "state": row["state"],
                    "reason": row.get("reason"),
                }
                for row in history
            ],
        },
        "cycles": [deepcopy(row) for row in index["cycles"][device_id][-30:]],
        "incidents": [
            row
            for row in alert_rows(data, include_closed=True)
            if device_id in (row.get("device_ids") or [])
        ][:50],
        "profile": deepcopy(index["profiles"].get(device_id, {})),
        "sources": {
            "entity_refs": deepcopy(device.get("entity_refs", {})),
            "signals": deepcopy(device.get("signal", [])),
        },
        "period_days": days,
    }


def stock_summary(data: dict, *, days: int = 90, now: datetime | None = None) -> list:
    now = now or datetime.now(UTC)
    result = {}

    def entry(battery_type):
        key = str(battery_type or "Neznámy typ").strip().upper()
        return result.setdefault(
            key,
            {
                "battery_type": key,
                "installed_quantity": 0,
                "device_count": 0,
                "used_quantity": 0,
                "on_hand": None,
                "minimum": 0,
            },
        )

    devices = {row["device_id"]: row for row in data.get("devices", [])}
    for device in devices.values():
        if (
            device.get("power_type") == "replaceable_battery"
            and device.get("tracking_mode") != "ignored"
        ):
            row = entry(device.get("battery_type"))
            row["installed_quantity"] += int(device.get("battery_quantity") or 1)
            row["device_count"] += 1
    for cycle in data.get("cycles", []):
        device = devices.get(cycle["device_id"], {})
        stamp = parse_time(cycle.get("started_at"))
        if (
            stamp
            and now - timedelta(days=days) <= stamp <= now
            and cycle.get("provenance") == "user_confirmed"
            and device.get("power_type") != "rechargeable"
        ):
            entry(cycle.get("battery_type"))["used_quantity"] += int(
                cycle.get("battery_quantity") or 1
            )
    for saved in data.get("battery_stock", []):
        entry(saved["battery_type"]).update(
            on_hand=saved.get("on_hand"), minimum=saved.get("minimum", 0)
        )
    for row in result.values():
        row["suggested_reserve"] = max(row["minimum"], row["used_quantity"])
        row["basis"] = (
            "confirmed_replacements" if row["used_quantity"] else "manual_minimum"
        )
    return sorted(
        result.values(),
        key=lambda row: (-row["installed_quantity"], row["battery_type"]),
    )
