# Availability and evidence engine

Health state and likely cause are separate outputs. An unavailable entity is evidence, not a diagnosis.

## Health states

`initializing`, `healthy`, `degraded`, `stale`, `offline`, `recovering`, `paused`, `unknown`.

Use explicit source availability when available. Otherwise learn reporting behavior per device from selected sentinel entities and report timestamps. Calculate robust intervals (median and upper quantiles plus dispersion); do not apply one global timeout. A device that reports only on events cannot be declared offline from silence unless another reliable source establishes expected activity.

Candidate transition logic: healthy → degraded → stale → offline as missed expected reporting windows accumulate; recovering after a fresh report; healthy after a stability window. Threshold multipliers and stability windows remain tunable/open. Startup grace prevents alerts while HA and source integrations initialize.

## Cause hypotheses

- `battery`: low/critical level, native battery-low, low voltage, abnormal rapid drain, unusually old cycle, or recovery after confirmed replacement.
- `connectivity`: weak/degrading signal, repeated individual dropouts, recovery without battery intervention, or provider-specific link evidence.
- `gateway_upstream`: correlated outage among devices sharing a coordinator, gateway, AP or source path; coordinator/source unavailable.
- `integration`: source config entry reload/failure or broad loss within one integration.
- `power_or_network`: shared host/network/power evidence where available.
- `unknown`: evidence absent, conflicting or below classification threshold.

## Scoring and explanation

Use an explainable evidence table, with positive and negative evidence for each hypothesis. Avoid a black-box label. Candidate examples: battery at 3% plus a sustained steep decline increases battery likelihood; 12 sibling devices failing together while the coordinator is unavailable strongly favors gateway/upstream. Scores/confidence should be calibrated and tested against labeled incidents before being exposed as probabilities.

Initial proposed classification gate (to validate, not a committed constant): top score at least 60 and at least 15 points above the runner-up. Otherwise `unknown`. Keep confidence semantics explicit; raw scores are not probabilities unless calibrated.

## Correlation and revision

Cluster incidents by overlapping onset and shared dependency/source. One parent incident can suppress a flood of duplicate device alerts; affected devices retain links to it and may inherit a likely upstream cause. Use time windows and dependency evidence to avoid grouping unrelated outages.

Causes may change as evidence arrives. Preserve initial and revised classification, evidence and timestamps. A manually confirmed battery replacement followed by recovery may confirm a battery cause; an unassisted recovery with stable battery can strengthen connectivity evidence. Do not silently rewrite history.

## Alert behavior

Debounce, cooldown, deduplication, startup grace, maintenance/snooze and optional recovery notifications. Notification delivery uses HA's normal notification mechanisms/actions; HA Repairs are not the general incident-alert channel.
