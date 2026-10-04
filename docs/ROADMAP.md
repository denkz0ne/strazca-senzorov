# Development stages

The original sequence was a planning order. Implementation was delivered through GitHub tasks 0–9, and responsibilities moved between tasks as HA API probes and tests exposed dependencies. Current state is recorded below; completed implementation does not mean release validation is complete.

## Current stage status

| Stage | State | Evidence / remaining work |
| --- | --- | --- |
| 0 — specification and compatibility | Implemented | ADRs record the Core floor, device linking and filtered report evidence. Re-run compatibility checks before release. |
| 1 — integration scaffold and storage | Implemented | Config flow, setup/unload, schema 1.1, translations and tests are present. |
| 2 — Battery Notes import and model catalogue | Implemented | One-time preview/apply, backup/receipt, provenance and bundled converted catalogue; live import and restore remain unverified. |
| 3 — battery lifecycle and estimate | Implemented | Samples, replacement cycles and conservative per-device estimator; real-world estimate quality still needs observation. |
| 4 — discovery and tracking | Implemented on PR #15; CI passed | Compact battery/device/overview tables, name/area identity, selection filters and native discovery notices are implemented. GitHub Actions run `37235438288` passed Ruff, JavaScript/JSON validation, all 73 tests and the HACS action. Per-panel badge remains unsupported by HA's public API; live HA pairing/viewport review remains pending. |
| 5 — availability and reporting learner | Implemented | Filtered source listeners and learned profiles; provider-specific validation and false-positive calibration remain. |
| 6 — cause evidence and incident clustering | Implemented | Rule points, unknown threshold and incident revisions are covered in CI; labeled live incident calibration remains. |
| 7 — entities, actions and events | Implemented | Compact entities and version-1 actions/events exist; release compatibility review remains. |
| 8 — panel and authenticated API | Implemented, live smoke review partial | Compact tables, sticky section/search controls and discovery notice pass local syntax/lint/frontend asset checks; CI and actual HA browser layout/HACS clean-install/update remain release checks. |
| 9 — release hardening | In progress | See `docs/RELEASE_CHECKLIST.md`; no stable tag/release has been made. |

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
