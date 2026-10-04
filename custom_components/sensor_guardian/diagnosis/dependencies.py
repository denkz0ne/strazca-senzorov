"""Shared-dependency indexing and time-bounded outage clustering."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from itertools import combinations
from typing import Any


def _dependency_id(kind: str, key: str) -> str:
    return f"dep_{hashlib.sha256(f'{kind}:{key}'.encode()).hexdigest()[:16]}"


def build_dependencies(devices: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group records only by explicit shared provider/gateway/config-entry IDs."""
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for device in devices:
        for kind, key in (
            ("provider", device.get("provider_ref")),
            ("config_entry", device.get("config_entry_id")),
        ):
            if isinstance(key, str) and key:
                groups.setdefault((kind, key), []).append(device)
    return [
        {
            "dependency_id": _dependency_id(kind, key),
            "kind": kind,
            "provider_ref": key if kind == "provider" else None,
            "source_integration": key if kind == "source_integration" else None,
            "config_entry_id": key if kind == "config_entry" else None,
            "device_ids": sorted(
                {
                    device["device_id"]
                    for device in members
                    if isinstance(device.get("device_id"), str)
                }
            ),
        }
        for (kind, key), members in groups.items()
        if len({device.get("device_id") for device in members}) >= 2
    ]


def correlated_clusters(
    outages: list[dict[str, Any]],
    dependencies: list[dict[str, Any]],
    *,
    window_seconds: int = 300,
    minimum_devices: int = 3,
) -> list[dict[str, Any]]:
    """Cluster overlapping outages only when they share explicit dependencies."""
    dependency_members: dict[str, set[str]] = {}
    for dependency in dependencies:
        members = dependency.get("device_ids", [])
        if isinstance(members, list):
            for device_id in members:
                if isinstance(device_id, str):
                    dependency_members.setdefault(
                        dependency["dependency_id"], set()
                    ).add(device_id)
    by_id = {
        outage.get("device_id"): outage
        for outage in outages
        if isinstance(outage.get("device_id"), str)
    }
    adjacency: dict[str, set[str]] = {device_id: set() for device_id in by_id}
    linked_dependency: dict[tuple[str, str], str] = {}
    for dependency_id, members in dependency_members.items():
        for left, right in combinations(sorted(members.intersection(by_id)), 2):
            start_left = _date(by_id[left].get("opened_at"))
            start_right = _date(by_id[right].get("opened_at"))
            if (
                start_left
                and start_right
                and abs((start_left - start_right).total_seconds()) <= window_seconds
            ):
                adjacency[left].add(right)
                adjacency[right].add(left)
                linked_dependency[(left, right)] = dependency_id
    clusters: list[dict[str, Any]] = []
    visited: set[str] = set()
    for device_id in adjacency:
        if device_id in visited:
            continue
        stack, component = [device_id], set()
        while stack:
            current = stack.pop()
            if current in component:
                continue
            component.add(current)
            stack.extend(adjacency[current] - component)
        visited.update(component)
        if len(component) < minimum_devices:
            continue
        matching = [
            dep_id
            for (left, right), dep_id in linked_dependency.items()
            if left in component and right in component
        ]
        clusters.append(
            {
                "device_ids": sorted(component),
                "dependency_id": max(set(matching), key=matching.count),
                "opened_at": min(by_id[item]["opened_at"] for item in component),
            }
        )
    return clusters


def _date(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return (
        parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)
    )
