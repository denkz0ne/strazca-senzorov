"""Notification policy is independent from collection and automation events."""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from .history import parse_time


def allowed(
    data: dict, device: dict, *, now: datetime | None = None, time_zone: str = "UTC"
) -> bool:
    current = now or datetime.now(UTC)
    settings, rules = data.get("settings", {}), device.get("rules", {})
    if (
        not settings.get("notifications_enabled", True)
        or rules.get("notifications_enabled") is False
    ):
        return False
    snooze = parse_time(device.get("snoozed_until"))
    if snooze is not None and current < snooze:
        return False
    if rules.get("criticality") == "critical":
        return True
    start, end = settings.get("quiet_start", ""), settings.get("quiet_end", "")
    if start and end:
        minute = current.astimezone(ZoneInfo(time_zone)).strftime("%H:%M")
        quiet = (
            start <= minute < end if start < end else minute >= start or minute < end
        )
        if quiet:
            return False
    return True


def repeat_due(data: dict, incident: dict, now: datetime) -> bool:
    minutes = int(data.get("settings", {}).get("notification_repeat_minutes", 0))
    previous = parse_time(incident.get("last_notified_at"))
    return bool(
        minutes > 0
        and previous
        and not incident.get("acknowledged")
        and incident.get("notification_state") == "sent"
        and (now - previous).total_seconds() >= minutes * 60
    )


def battery_notice(hass, data: dict, device: dict) -> None:
    from homeassistant.components.persistent_notification import async_create

    from .const import DOMAIN

    latest = next(
        (
            row
            for row in reversed(data["samples"])
            if row["device_id"] == device["device_id"]
            and row.get("level_percent") is not None
        ),
        None,
    )
    level = f"{latest['level_percent']:g} %" if latest else "neznáma"
    async_create(
        hass,
        f"{device.get('name') or 'Sledované zariadenie'}: batéria vyžaduje pozornosť. "
        f"Posledná úroveň: {level}. "
        "Podrobnosti sú v [Strážcovi senzorov](/sensor_guardian).",
        title="Strážca senzorov — batéria",
        notification_id=f"{DOMAIN}_battery_{device['device_id']}",
    )
