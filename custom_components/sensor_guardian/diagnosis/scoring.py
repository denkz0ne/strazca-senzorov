"""Explainable cause scores with a conservative unknown classification gate."""

from __future__ import annotations

from typing import Any

MIN_CAUSE_SCORE = 60
MIN_CAUSE_MARGIN = 15


def score_evidence(evidence: list[dict[str, Any]]) -> dict[str, Any]:
    """Score labeled evidence rules; points are not probabilities."""
    scores = {
        cause: 0
        for cause in (
            "battery",
            "connectivity",
            "gateway_upstream",
            "integration",
            "power_or_network",
        )
    }
    explanations: dict[str, list[str]] = {cause: [] for cause in scores}

    def add(cause: str, points: int, explanation: str) -> None:
        scores[cause] += points
        explanations[cause].append(f"{points:+d}: {explanation}")

    for item in evidence:
        feature, value = item.get("feature"), item.get("value")
        if item.get("quality") in {"invalid", "stale", "untrusted"}:
            continue
        if feature == "battery_level" and isinstance(value, (int, float)):
            if value <= 5:
                add("battery", 50, "battery reading is at or below 5 percent")
            elif value <= 15:
                add("battery", 35, "battery reading is at or below 15 percent")
            elif value <= 25:
                add("battery", 15, "battery reading is low")
        elif feature == "native_battery_low" and value is True:
            add("battery", 35, "device reports native battery-low")
        elif feature == "voltage_low" and value is True:
            add("battery", 20, "measured voltage is below configured profile")
        elif feature == "abnormal_drain" and value is True:
            add("battery", 25, "drain is unusually fast for this device")
        elif feature == "recovered_after_replacement" and value is True:
            add("battery", 35, "device recovered after a confirmed replacement")
        elif feature == "recovered_without_battery_change" and value is True:
            add("battery", -20, "device recovered without battery intervention")
            add("connectivity", 25, "device recovered without battery intervention")
        elif feature == "signal_trend" and value == "degrading":
            add("connectivity", 25, "signal quality is degrading")
        elif feature == "rssi_dbm" and isinstance(value, (int, float)) and value <= -90:
            add("connectivity", 20, "radio signal is very weak")
        elif (
            feature in {"lqi", "linkquality"}
            and isinstance(value, (int, float))
            and value <= 40
        ):
            add("connectivity", 20, "link quality is very weak")
        elif feature == "single_device_dropout" and value is True:
            add("connectivity", 10, "only this device is affected")
        elif (
            feature in {"coordinator_unavailable", "gateway_unavailable"}
            and value is True
        ):
            add("gateway_upstream", 55, "shared coordinator or gateway is unavailable")
        elif feature == "shared_outage_count" and isinstance(value, int) and value >= 3:
            add(
                "gateway_upstream",
                min(35, 15 + value * 4),
                f"{value} devices sharing a dependency failed together",
            )
        elif feature == "source_entry_unavailable" and value is True:
            add("integration", 50, "source integration config entry is unavailable")
        elif (
            feature == "source_entry_outage_count"
            and isinstance(value, int)
            and value >= 3
        ):
            add(
                "integration",
                min(30, 10 + value * 3),
                f"{value} devices from this source integration are affected",
            )
        elif (
            feature in {"network_unavailable", "host_power_unavailable"}
            and value is True
        ):
            add(
                "power_or_network",
                55,
                "shared host or network infrastructure is unavailable",
            )
        elif feature == "signal_stable" and value is True:
            add("connectivity", -10, "signal remained stable before the outage")
        elif feature == "battery_stable" and value is True:
            add("battery", -10, "battery readings remained stable before the outage")
    scores = {cause: min(100, max(0, value)) for cause, value in scores.items()}
    ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    return {
        "scores": scores,
        "ranked_causes": [
            {"cause": cause, "score": score, "reasons": explanations[cause]}
            for cause, score in ranked
        ],
        "score_semantics": "evidence_points_not_probability",
    }


def classify_cause(
    scoring: dict[str, Any],
    *,
    min_score: int = MIN_CAUSE_SCORE,
    min_margin: int = MIN_CAUSE_MARGIN,
) -> dict[str, Any]:
    """Return unknown unless top score and separation both meet the gate."""
    ranked = scoring.get("ranked_causes", [])
    if not ranked:
        return {"cause": "unknown", "confidence": "none", "reason_code": "no_evidence"}
    top = ranked[0]
    second_score = ranked[1]["score"] if len(ranked) > 1 else 0
    margin = top["score"] - second_score
    if top["score"] < min_score:
        reason = "score_below_threshold"
        cause = "unknown"
    elif margin < min_margin:
        reason = "competing_evidence"
        cause = "unknown"
    else:
        reason = "score_and_margin_met"
        cause = top["cause"]
    return {
        "cause": cause,
        "confidence": "high"
        if cause != "unknown" and top["score"] >= 80
        else "medium"
        if cause != "unknown"
        else "none",
        "reason_code": reason,
        "top_score": top["score"],
        "margin": margin,
        "score_semantics": "evidence_points_not_probability",
    }
