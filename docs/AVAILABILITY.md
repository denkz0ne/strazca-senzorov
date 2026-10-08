# Availability and evidence engine

Health state and likely cause are separate outputs. An unavailable entity is evidence, not a diagnosis.

## Health states

`initializing`, `healthy`, `degraded`, `stale`, `offline`, `recovering`, `paused`, `unknown`, `not_monitored`.

Use explicit source availability when available. Otherwise learn reporting behavior per device from selected sentinel entities and report timestamps. Calculate robust intervals (median and upper quantiles plus dispersion); do not apply one global timeout. A device that reports only on events cannot be declared offline from silence unless another reliable source establishes expected activity.

Candidate transition logic: healthy → degraded → stale → offline as missed per-device learned reporting windows accumulate; recovering after a fresh report; healthy after a stability window. The initial implementation uses 1.25× p90 for degraded, 1.5× p95 for stale and 3× p95 for offline, with a 30-second minimum. Explicit native availability takes precedence. Devices with event-only or low-confidence report patterns stay `unknown` on silence rather than being declared offline. Startup grace defaults to five minutes and recovery stability to two minutes; values are conservative implementation defaults to revisit against real devices.

In 0.1.1, an explicit connectivity sensor remains authoritative. Without one, a selected primary source supplies HA availability: an actuator is preferred for mains devices, so cached numeric telemetry cannot conceal its unavailable state. Source availability can establish healthy while periodicity is learning; source unavailability establishes offline after startup grace. Missing/unknown sources with no confident cadence remain unknown. A cached valid HA state is not proof of recent physical radio traffic. Intentional battery-only tracking is not_monitored; disabling availability closes its incidents without asserting physical recovery.

The collector observes only the selected sentinel IDs and any explicitly selected native availability entity. It listens separately for state changes and same-state `state_reported` events, then seeds the current states immediately after registering listeners. A bounded 512-report rolling timestamp window feeds each device's independent median/p90/p95 and jitter profile. Unload removes both filtered subscriptions and cancels pending persistence.

Cadence is learned from one canonical report source, avoiding artificial microsecond intervals from concurrent multi-entity writes. Source state changes still trigger health evaluation. Runtime work is coalesced; a pending ten-second save is not moved later by continuous reports, and unload persists pending observations.

## Cause hypotheses

- `battery`: low/critical level, native battery-low, low voltage, abnormal rapid drain, unusually old cycle, or recovery after confirmed replacement.
- `connectivity`: weak/degrading signal, repeated individual dropouts, recovery without battery intervention, or provider-specific link evidence.
- `gateway_upstream`: correlated outage among devices sharing a coordinator, gateway, AP or source path; coordinator/source unavailable.
- `integration`: source config entry reload/failure or broad loss within one integration.
- `power_or_network`: shared host/network/power evidence where available.
- `unknown`: evidence absent, conflicting or below classification threshold.

## Scoring and explanation

Use an explainable evidence table, with positive and negative evidence for each hypothesis. The initial rule-based engine uses named evidence points: critically low percent, native battery-low, abnormal drain, signal decline, weak RSSI/LQI, explicit coordinator/gateway/source-entry loss, shared outage count and recovery without battery intervention. Every applied rule appears with its signed point contribution. Candidate examples: battery at 3% plus a native low flag strongly increases battery points; several siblings failing together while their coordinator is unavailable strongly favors gateway/upstream. The score is an internal evidence-point total, never a percentage/probability.

Initial classification gate: top score at least 60 and at least 15 points above the runner-up. Otherwise `unknown`. The rules produce only low/medium/high confidence labels from point bands; those labels are qualitative and are not calibrated probabilities.

When dropout removes current battery values, the latest usable battery facts from the previous seven days can supply dated evidence. Invalid/stale samples are excluded. The panel still distinguishes current readings from retained historical data.

## Correlation and revision

Cluster incidents by overlapping onset and shared dependency/source. One parent incident can suppress a flood of duplicate device alerts; affected devices retain links to it and may inherit a likely upstream cause. Use time windows and dependency evidence to avoid grouping unrelated outages.

Causes may change as evidence arrives. Preserve initial and revised classification, evidence and timestamps. A manually confirmed battery replacement followed by recovery may confirm a battery cause; an unassisted recovery with stable battery can strengthen connectivity evidence. Do not silently rewrite history.

## Alert behavior

Debounce, cooldown, deduplication, startup grace, maintenance/snooze and optional recovery notifications. Notification delivery uses HA's normal notification mechanisms/actions; HA Repairs are not the general incident-alert channel.

## 0.2.0 availability and prevention

Communication health, battery attention, prediction confidence and data quality are independent. A valid HA state may give healthy availability while the report cadence is still learning; the dashboard still lists incomplete interval coverage. Stored HA timestamps are not asserted as newly received physical packets. Offline causes remain unknown when evidence is insufficient; owner-confirmed causes are retained.

Independent battery incidents include low/native-low, rapid-drain and supported replacement warnings. Availability incidents group shared outages and remove prior child native notices. Temporary snooze resumes unresolved delivery after expiry; acknowledgment suppresses repetition of the current incident. Quiet hours use HA timezone, with explicit critical-device exception. Collection and automation events continue while native delivery is suppressed. Repeat rules apply to battery and availability alerts, including device overrides.
