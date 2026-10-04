# Development stages

Order is provisional and intended to reduce rework by validating data access before investing in the panel.

## Stage 0 — specification and compatibility probe

Set domain/display name, supported HA minimum, storage strategy, entity contract and migration scope. Inspect actual target HA APIs and Battery Notes version/storage. Validate device linking, `last_reported`/selected report evidence, Recorder/statistics read access, and disabled signal entity handling. Domain and initial Core floor are recorded in `docs/decisions/0001-ha-compatibility.md`; helper linking and report evidence are in `docs/decisions/0002-entity-linking-and-report-evidence.md`.

## Stage 1 — integration scaffold

Create manifest, config flow/options, translations, diagnostics, storage schema/versioning, device tracking model and minimal integration tests. Confirm stable device/entity links and unload/reload behavior.

## Stage 2 — Battery Notes one-time importer

Convert a pinned upstream library snapshot, preserve notices, import per-device settings, inspect Recorder/statistics, preview uncertain history, ensure idempotence, backup/restore and receipt. Validate before user removes Battery Notes.

## Stage 3 — battery lifecycle and estimator

Record samples and explicit replacements; detect candidate replacements for confirmation; distinguish rechargeable charging; compute robust trends, abnormal drain, remaining range and confidence using per-device replacement history.

## Stage 4 — discovery and tracking configuration

Recommend battery+availability, availability-only, battery-only, ignore or unknown. Pre-fill device metadata; keep unknown-device setup short; allow model-wide defaults with explicit user choice.

## Stage 5 — generic availability engine

Implement explicit availability and selected sentinel tracking, learned per-device reporting patterns, health states, startup grace and recovery. Validate event-driven-device handling.

## Stage 6 — evidence/cause and provider adapters

Add explainable cause scoring, thresholds for unknown, incident revision and dependency correlation. Start with generic HA evidence; prioritize ZHA and other adapters from actual devices/proof of useful accessible data.

## Stage 7 — incidents, events and notifications

Add grouping, acknowledgement, deduplication, cooldown/snooze, compact events and HA actions. Keep entity count small.

## Stage 8 — panel

MVP implementation: self-hosted admin-only Home Assistant custom panel, authenticated paginated WebSocket API, overview, battery catalogue/history and assignments, discovery recommendations, incidents, settings, Battery Notes preview/apply, and local battery-model additions. Release hardening still needs a live HA/HACS browser and upgrade pass.

## Stage 9 — validation and release

Validate schema upgrades, restart/reload, recorder-unavailable cases, long-running devices, false-positive rates, translations, HACS packaging, license notices and docs. Release only with documented support/limitations and migration backup guidance.

## MVP boundary

The first usable release should prioritize generic availability tracking, battery replacement records, basic history-based battery attention, concise HA entities/events, and a functional panel. Advanced per-protocol root-cause certainty and cohort prediction can follow after real labeled observations exist.
