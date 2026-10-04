# Strážca senzorov Development Plan

> **For agentic workers:** Execute this plan one GitHub issue at a time. Keep each task's changes reviewable, run only the verification listed for that task, report the outcome, and do not start a dependent task until its prerequisite is complete.

**Goal:** Build a Home Assistant integration that monitors device availability and battery lifecycle, explains likely outage causes with calibrated uncertainty, and exposes concise automation interfaces plus a detailed side panel.

**Architecture:** Start with a small helper integration and a generic HA evidence collector. Keep durable configuration, observations, profiles, replacement cycles and incidents in versioned Strážca storage. Separate availability state, battery estimation and cause classification; connect them through normalized evidence and incident records. Source entities stay authoritative, while a minimal HA entity/event/action layer serves automations and the panel serves detail.

**Tech Stack:** Python custom integration for Home Assistant Core `2026.9+`; HA config/device/entity registries, storage and event APIs; HA entity platforms and service actions; a bundled web frontend and HA panel registration (implementation mechanism to validate); GitHub Actions/HACS packaging.

**Spec:** `README.md`, `docs/ARCHITECTURE.md`, `docs/DATA_MODEL.md`, `docs/MIGRATION.md`, `docs/AVAILABILITY.md`, `docs/HOME_ASSISTANT.md`, `docs/FRONTEND.md`, `docs/ROADMAP.md`, `docs/OPEN_QUESTIONS.md`.

## Global Constraints

- Integration domain is `sensor_guardian`; validate custom-integration compatibility again before the first public release because the domain is costly to change.
- Initial target is HA Core `2026.9.4`; proposed minimum is Core `2026.9`, pending compatibility validation before release.
- Battery Notes is a one-time migration source only; Strážca must not require it at runtime and the user removes it only after verifying a successful import/deployment.
- Runtime observations come from HA device entities, including battery %, native battery-low, voltage, availability, signal/link-quality and report-time evidence where available.
- Never listen globally to high-volume `state_reported`; use a filtered subscription for explicitly selected entities and validate cost at the supported HA minimum.
- Link helper entities to the source device using the supported helper-integration API; do not attach Strážca's config entry to a source device.
- Preserve provenance and distinguish observed, inferred and user-confirmed data. `unknown` is a valid health/cause result.
- Store only useful samples and checkpoints; HA Recorder is an optional migration/bootstrap source, not Strážca's durable history.
- Mains devices receive availability monitoring only. Recharge events do not create replacement records.
- Detailed statistics stay in the panel; default HA entities remain limited and automation-focused.
- Every data/schema change must preserve existing user data or provide a recoverable migration path.

## Review Focus

- **Noisy or event-only entities:** silence must not falsely declare offline; select tests with stable, irregular and event-only report patterns in Tasks 5–6.
- **Shared outage:** correlated devices should create a parent incident and avoid alert floods; exercise sibling failures and a single-device failure in Task 6.
- **Uncertain cause:** competing evidence must resolve to `unknown`; test low, conflicting and high-margin evidence in Task 6.
- **Battery jumps/recharge:** ignore transient percentage jumps and do not treat rechargeable charging as replacement; test in Tasks 3–4.
- **Migration loss/duplication:** imported history must be provenance-tagged, reviewable, recoverable and idempotent; test repeat import, partial data and backup restore in Task 3.

---

## Task 0: Confirm API and project contracts

**Files:**
- Create: `docs/decisions/0001-ha-compatibility.md`
- Create: `docs/decisions/0002-entity-linking-and-report-evidence.md`
- Update: `docs/OPEN_QUESTIONS.md`

**Interfaces:** produces the supported HA version floor, a checked integration/manifest pattern, entity-to-device linking method, report-time listener constraints, storage API expectations and a decision on domain `sensor_guardian`.

- [x] Record target Home Assistant Core version `2026.9.4` from `/config/.HA_VERSION`; set the initial minimum at Core `2026.9`.
- [x] Verify helper linking against Core 2026.9.4 and current official guidance; record `homeassistant.helpers.device.async_entity_id_to_device` and reject source-device config-entry attachment.
- [x] Verify `last_reported`/`state_reported` semantics and event filtering requirements; record selected-entity tracking and startup behavior.
- [x] Verify custom integration manifest, config flow and storage requirements for the chosen release range.
- [x] Decide open blockers for a production release; update this plan and the open-question list.

**Exit check:** decisions cite versioned official Home Assistant documentation and identify any behavior requiring a running-instance probe. Do not ship a manifest until the domain and version floor are explicit.

## Task 1: Scaffold integration and development checks

**Files:**
- Create: `custom_components/sensor_guardian/manifest.json`, `__init__.py`, `const.py`, `config_flow.py`, `strings.json`, `translations/en.json`, `translations/sk.json`
- Create: `tests/conftest.py`, `tests/test_config_flow.py`, `pyproject.toml` (or the selected project config), `.github/workflows/validate.yml`
- Modify: `README.md` to document installation/development status

**Interfaces:** `DOMAIN = "sensor_guardian"`; config flow creates one integration entry with no polling or entities yet; setup/unload are reversible and register/unregister only owned resources.

- [x] Add setup/config-flow coverage (Linux runner verification pending) for the approved domain, duplicate config entry and successful unload.
- [x] Add only the dependencies and formatting/type/lint configuration required by the selected HA test environment.
- [x] Implement the empty integration scaffold and translations.
- [x] Run the scoped config-flow tests and static checks; confirm no background listener survives unload.
- [x] Commit the scaffold as one reviewable unit.

**Exit check:** the integration can be loaded and unloaded in the declared development environment without changing source devices or registering product entities.

## Task 2: Versioned storage and normalized domain records

**Files:**
- Create: `custom_components/sensor_guardian/storage.py`, `models.py`, `migrations.py`
- Create: `tests/test_storage.py`, `tests/test_migrations.py`
- Modify: `custom_components/sensor_guardian/__init__.py`

**Interfaces:** typed versioned records for model definitions, tracked devices, samples, battery cycles, availability profiles, dependencies, incidents and settings as defined in `docs/DATA_MODEL.md`; storage owns load/save/migrate/export and does not call the Recorder for ongoing persistence.

- [x] Pin a JSON-serializable schema and fixtures for an empty installation and one device record.
- [ ] Test initial load, atomic save/reload, malformed data preservation, idempotent migration and unknown future schema handling.
- [x] Implement the HA Store wrapper and pure record conversion/validation functions.
- [x] Run the scoped storage/migration tests; inspect that the original data remains recoverable on failure.
- [x] Commit.

## Task 3: Discovery, tracking configuration and Battery Notes importer

**Files:**
- Create: `custom_components/sensor_guardian/discovery.py`, `migration/battery_notes.py`, `migration/__init__.py`
- Create: `custom_components/sensor_guardian/data/battery_models.json` and required upstream license/attribution notice after snapshot selection
- Create: `tests/test_discovery.py`, `tests/migration/test_battery_notes.py`
- Modify: `docs/MIGRATION.md`, `THIRD_PARTY_DATA.md`

**Interfaces:** discovery returns candidates with source entity references, confidence, explanation and one suggested mode (`battery_and_availability`, `availability_only`, `battery_only`, `ignore`, `unknown`). Import preview returns matched/unmatched counts and proposed updates with provenance; apply is idempotent and creates a receipt. No import runs silently.

- [x] Pin the Battery Notes commit/release and inspect the actual data license/notice before copying any row.
- [x] Add fixtures covering duplicate model records/variants, missing device IDs, and rechargeable/irreplaceable hints.
- [x] Implement device/entity registry discovery and candidate ranking; accept persisted tracked/dismissed IDs and preserve manual settings in import merges.
- [x] Implement preview for catalogue count and per-device settings; add a bounded, selected-entity Recorder/history statistics adapter with distinct exact/inferred provenance.
- [x] Test partial import, repeat import, backup/restore, stale/unmatched source device and malformed source data.
- [x] Add explicit signal-entity recommendations; discovery does not enable entities.
- [x] Run scoped discovery/migration verification and commit catalogue provenance with the imported dataset.

**Exit check:** Strážca operates with Battery Notes absent after a verified import; no runtime code calls Battery Notes or its remote repository.

## Task 4: Battery lifecycle and remaining-life estimator

**Files:**
- Create: `custom_components/sensor_guardian/battery/engine.py`, `samples.py`, `replacement.py`, `estimator.py`
- Create: `tests/battery/test_samples.py`, `test_replacement.py`, `test_estimator.py`
- Modify: `custom_components/sensor_guardian/models.py`

**Interfaces:** pure functions normalize readings, detect replacement candidates, maintain a cycle and return estimate `{remaining_days_range, replacement_window, confidence, reason_codes}`; they do not create HA entities or notifications.

- [x] Define bounds/quality flags for invalid %, voltage and timestamps; cover percentage jitter and stale reports.
- [x] Record only meaningful changes/checkpoints and flag low-battery, significant voltage changes and confirmed replacement.
- [x] Distinguish disposable replacement from rechargeable charge; require confirmation for uncertain automatic replacement candidates.
- [x] Implement robust trend estimation plus per-device cycle-history comparison; expose no ETA below the documented sample-quality gate.
- [x] Detect abnormal drain against the device's own prior cycles and mark weak/coarse sensor reports as low quality.
- [x] Test flat, noisy, steep-drop, sparse, reset-after-replacement and charging traces; run battery tests and commit.

## Task 5: Generic availability and reporting-pattern learner

**Files:**
- Create: `custom_components/sensor_guardian/availability/collector.py`, `profile.py`, `engine.py`
- Create: `tests/availability/test_profile.py`, `test_engine.py`, `test_subscriptions.py`
- Modify: `custom_components/sensor_guardian/__init__.py`, `models.py`

**Interfaces:** collector observes only tracked sentinel/native-availability entities; profile learner returns interval distribution and pattern confidence; engine emits health transitions without assigning a cause.

- [x] Test stable, jittery, irregular and event-only input traces, including `unknown`/`unavailable` source states.
- [x] Add explicit-native-availability precedence, selected sentinel subscriptions with event filtering and immediate state seeding, startup grace and clean unsubscribe on unload.
- [x] Implement per-device degraded/stale/offline/recovering transitions and recovery stability window; do not use one global one-hour threshold.
- [x] Confirm disabled/noisy entities do not cause unbounded event work; run scoped availability checks and commit.

## Task 6: Evidence, dependencies and clustered incidents

**Files:**
- Create: `custom_components/sensor_guardian/diagnosis/evidence.py`, `scoring.py`, `dependencies.py`, `incidents.py`
- Create: `tests/diagnosis/test_scoring.py`, `test_correlation.py`, `test_revision.py`
- Modify: `custom_components/sensor_guardian/models.py`, `docs/AVAILABILITY.md`

**Interfaces:** scoring consumes normalized timestamped evidence and returns ordered cause scores plus explanations; classification returns `unknown` unless the validated threshold and margin are met. Incident manager supports open/update/close, parent/affected devices, acknowledgement, snooze and cause revision audit.

- [x] Add labeled fixtures for low-battery dropout, one-device RF dropout, coordinator/source outage, simultaneous shared outage, recovery without intervention and conflicting evidence.
- [x] Implement documented score reasons and ensure raw scores are not exposed as probabilities unless calibrated.
- [x] Correlate incidents through overlap and known shared dependencies; avoid grouping unrelated single-device incidents.
- [x] Add cause revision history and explicit confirmed/inferred classification provenance.
- [x] Run scoring/correlation tests and review false-positive scenarios; commit.

## Task 7: Minimal HA entities, actions and event contracts

**Files:**
- Create: `custom_components/sensor_guardian/binary_sensor.py`, `sensor.py`, `services.py`, `services.yaml`, `events.py`
- Create: `tests/test_entities.py`, `tests/test_actions.py`, `tests/test_events.py`
- Modify: `custom_components/sensor_guardian/__init__.py`, `strings.json`, translations

**Interfaces:** initially expose per tracked device `guardian_problem`, optional `guardian_status`, and battery-only `battery_attention`; service actions use device/incident selectors. Fire versioned incident/recovery/battery-attention/replacement events from `docs/HOME_ASSISTANT.md`.

- [x] Test entity unique IDs, availability, state transitions, removal and source-device linking on the supported HA version.
- [x] Keep signal, battery type, quantity, cycle stats and confidence detail out of default entity inventory.
- [x] Implement mark-replaced, confirm-cause, snooze and resume actions with input validation and idempotence.
- [x] Test event names/payload version, transitions only (no duplicate spam), no secret/unrelated state leakage and unload cleanup.
- [x] Resolve whether guardian status and guardian problem are both default or one is optional; update docs and translations before API freeze.
- [x] Run scoped entity/action/event verification and commit.

## Task 8: Side panel and internal API

**Files:**
- Create: `custom_components/sensor_guardian/panel.py`, `websocket_api.py`, frontend source/build files (paths selected from the project framework decision)
- Create: `tests/test_websocket_api.py` plus frontend unit/build checks
- Modify: `docs/FRONTEND.md`, `README.md`

**Interfaces:** authenticated HA WebSocket commands provide paginated overview, device detail, battery catalogue/history, discovery decisions, incidents and settings; mutations call the same backend operations as HA actions. Frontend never owns durable state.

- [x] Decide frontend packaging/panel registration approach compatible with supported HA versions and HACS install/update: self-hosted custom panel module inside the integration directory, no external runtime assets/build dependency.
- [x] Define validated read/write command schemas, pagination and error responses; reject unknown device/model IDs safely.
- [x] Implement tabs for Overview, Batteries, Devices, Incidents and Settings from `docs/FRONTEND.md`.
- [x] Review keyboard focus/semantics, narrow viewport rules, empty/partial data, `unknown` cause, import preview and disabled-signal recommendation states in the self-hosted UI and API.
- [x] Run API/frontend syntax and focused integration checks; commit. Live HA browser inspection remains a release gate in Task 9.

## Task 9: Release hardening and HACS delivery

**Files:**
- Create/modify: `hacs.json`, `.github/workflows/validate.yml`, `README.md`, `CHANGELOG.md`, release checklist and license notices
- Modify: manifest/version and translations as required

- [ ] Validate install, config flow, startup, unload, restart, storage upgrade, export/restore and HACS packaging against the selected HA versions.
- [x] Validate no Battery Notes manifest/runtime dependency and no global `state_reported` listener.
- [x] Review generated entity count, selected-entity report-processing volume, alert deduplication and explanatory cause evidence on a labeled fixture set.
- [x] Document supported provider evidence, known limitations, one-time migration and removal procedure.
- [x] Add HACS packaging metadata, HACS repository validation to CI, JavaScript syntax/JSON checks, changelog and first-release checklist.
- [ ] Publish a tagged release only after CI passes and the user's intended deployment path is confirmed.

## Execution and reporting cadence

1. Keep this plan's task checkboxes current and mirror each task as one GitHub issue in milestone **MVP Development**.
2. Before starting a task, report its goal, dependencies and acceptance check in this chat; after it finishes, report changed files, evidence/verification and remaining risks.
3. Update `docs/PROGRESS.md` and close the matching GitHub issue only after the task's exit check is met.
4. Commit and push one independently reviewable task at a time. Do not make production deployment/release changes without an explicit release request.

### GitHub issue map

Milestone: [MVP Development](https://github.com/denkz0ne/strazca-senzorov/milestone/1)

| Plan task | GitHub issue |
|---|---|
| Task 0 — API and project contracts | [#1](https://github.com/denkz0ne/strazca-senzorov/issues/1) |
| Task 1 — Integration scaffold | [#2](https://github.com/denkz0ne/strazca-senzorov/issues/2) |
| Task 2 — Versioned storage | [#3](https://github.com/denkz0ne/strazca-senzorov/issues/3) |
| Task 3 — Discovery and Battery Notes importer | [#4](https://github.com/denkz0ne/strazca-senzorov/issues/4) |
| Task 4 — Battery lifecycle and estimator | [#5](https://github.com/denkz0ne/strazca-senzorov/issues/5) |
| Task 5 — Availability and report learner | [#6](https://github.com/denkz0ne/strazca-senzorov/issues/6) |
| Task 6 — Evidence and incident clusters | [#7](https://github.com/denkz0ne/strazca-senzorov/issues/7) |
| Task 7 — HA entities, actions and events | [#8](https://github.com/denkz0ne/strazca-senzorov/issues/8) |
| Task 8 — Side panel and API | [#9](https://github.com/denkz0ne/strazca-senzorov/issues/9) |
| Task 9 — Release hardening | [#10](https://github.com/denkz0ne/strazca-senzorov/issues/10) |

## Current verified source notes

- Home Assistant's helper-integration guidance says to link an entity to the source device via `device_entry`; adding the helper config entry to the source device is no longer supported from Core 2026.8: <https://developers.home-assistant.io/blog/2025/07/18/updated-pattern-for-helpers-linking-to-devices/>.
- `state_reported` is high-volume and requires entity filtering and immediate listener setup; do not subscribe globally: <https://developers.home-assistant.io/blog/2024/03/20/state_reported_timestamp/>.
- Custom integrations need a manifest and integration folder; configuration flow scaffold includes test/translation infrastructure: <https://developers.home-assistant.io/docs/creating_component_index/> and <https://developers.home-assistant.io/docs/creating_integration_file_structure/>.
- Storage threading/serialization behavior changed in 2025.11 and must be checked against the selected minimum: <https://developers.home-assistant.io/blog/2025/11/25/storage-helper-opt-in-serialize-in-executor/>.
