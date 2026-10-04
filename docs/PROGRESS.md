# Development progress

This log records completed work and verification for the staged development plan. Update it after each GitHub issue/task; keep user-facing updates in the active Codex conversation as requested.

## 2026-10-04 — development plan initialized

- Inspected `denkz0ne/strazca-senzorov` on GitHub: public repository, `main` branch, no existing issues, releases or workflows; repository currently contains the project proposal.
- Read the project documents and carried forward the confirmed Battery Notes one-time migration, entity-first observations, minimal HA entities, internal detailed panel and evidence-based `unknown` cause behavior.
- Checked official Home Assistant developer docs for helper entity linking, `state_reported`, custom integration scaffold/file structure and storage threading behavior. Captured the sourced constraints in the plan.
- Created a sequenced implementation plan. No product code, tests or HA instance settings were changed in this step.
- Created GitHub milestone [MVP Development](https://github.com/denkz0ne/strazca-senzorov/milestone/1) and issues [#1–#10](https://github.com/denkz0ne/strazca-senzorov/issues) mirroring Tasks 0–9.
- Follow-up: the plan was reviewed and the user approved continuous sequential execution on 2026-10-04.

## 2026-10-04 — Task 0 complete: compatibility contracts

- Read `/config/.HA_VERSION` through the read-only Home Assistant file tool: target Core is `2026.9.4`; set initial support floor to `2026.9` and record compatibility runs as a release gate.
- Verified the helper link against the official migration guidance and Core `2026.9.4` `utility_meter/select.py`: import `async_entity_id_to_device` from `homeassistant.helpers.device`, assign the returned `DeviceEntry` to `self.device_entry`, and do not attach the Strážca config entry to the source device.
- Verified `state_reported` filtering and `run_immediately`, custom manifest requirements (`version`, helper type, config flow, one config entry) and current Store serialization behavior in official docs.
- GitHub Core code search found no existing `sensor_guardian` domain in Core; selected that domain for the project. This did not check all third-party custom integrations.
- Added `docs/decisions/0001-ha-compatibility.md` and `docs/decisions/0002-entity-linking-and-report-evidence.md`; updated the open questions and plan.
- No product code or tests were changed in Task 0. Verification: target version read succeeded; Core 2026.9.4 source fetch succeeded; expected ADR/plan paths exist; `git diff --check` passed.
- Next: Task 1 scaffold and development checks (GitHub issue #2).

## 2026-10-04 — Task 1 in progress: integration scaffold

- Added the Python 3.14/HA 2026.9.4 test dependencies, Ruff configuration and Linux GitHub Actions validation workflow. Local Windows execution cannot collect HA tests because Core imports POSIX `fcntl`; no WSL or Docker runtime is available here, so full pytest verification is delegated to the repository workflow.
- Added three config-flow/setup tests, custom integration fixture support, manifest, single-instance flow, reversible empty setup/unload and English/Slovak translations.
- Documented development status and local commands in README. Runtime has no Battery Notes dependency, entities or report listener at this scaffold stage.
- Local verification so far: Ruff passes; `git diff --check` passes. HA pytest is pending GitHub Actions Linux run.

## 2026-10-04 — Task 1 complete: integration scaffold

- Added the Python 3.14 test environment, Ruff checks and GitHub Actions Linux workflow, plus the manifest, global config flow, reversible setup/unload and English/Slovak translations.
- Added a discovery assertion and config-flow/setup tests. The test fixture explicitly appends the repository's `custom_components` path because `pytest-homeassistant-custom-component` provides its own empty package path.
- Config entry is single-instance. Setup/unload creates no product entities and does not subscribe to `state_reported`.
- Verification: GitHub Actions run `37221295119` passed on commit `f67f33f`; Ruff passed and pytest passed all four tests against HA Core 2026.9.4. Local Ruff and `git diff --check` also passed. HA pytest is not runnable natively in this Windows environment because HA imports POSIX `fcntl`; Linux CI is the authoritative run.
- Task committed in the ongoing review branch. Next: Task 2, versioned storage and normalized domain records.

## 2026-10-04 — Task 2 complete: versioned storage and domain records

- Added TypedDict contracts for the model catalogue, tracked devices, battery samples/cycles, availability profiles, dependencies, incidents and settings, plus root payload validation with required stable IDs and extension-field retention.
- Added private, atomically written Home Assistant Store version 1.1 per config entry. Setup loads validated data; save validates before persistence; export emits a portable versioned envelope without HA's internal key.
- Added pure migration helpers for v1.0 → v1.1. Invalid payloads are rejected without a save; a future minor migration is rejected by Strážca and a future major version is rejected by Home Assistant Store.
- Documented the persisted schema and migration behavior in `docs/DATA_MODEL.md`.
- Verification: GitHub Actions run `37222830538` passed Ruff and all 13 HA pytest cases (config/discovery scaffold, storage, migration). Tests use the test plugin's `hass_storage` fixture, which exercises HA Store's migration and save paths; its storage backend is mocked, so actual filesystem atomic-write behavior is configured in Store and not physically validated by that fixture.
- Task committed on the review branch. Next: Task 3, entity discovery and one-time Battery Notes import.

## 2026-10-04 — Task 3 complete: discovery and one-time Battery Notes import

- Pinned the Battery Notes source to commit `df7c277cd43a42801aaf820329cb2ce365c1dbda`; verified its exact MIT notice and copied that notice beside our transformed catalogue. Converted the 2,331-row upstream snapshot to 2,330 deterministic internal model records, preserving semantic variants and model match rules. No Battery Notes runtime requirement or remote fetch was added.
- Added explainable discovery candidates from HA device/entity registry metadata and current state attributes. Ranking proposes battery+availability, battery-only, or availability-only only when evidence supports it; disabled signal entities are suggestions and are never enabled. Inputs for already tracked and dismissed IDs are supported.
- Added a preview-first importer for Battery Notes v1 Store snapshots and device config/subentry data, exact registry matches, unresolved records, latest replacement/report fields and pre-import backup. Import application is receipt-based/idempotent, does not replace an existing device choice, tags provenance, and validates restore data.
- Added a bounded Recorder adapter for selected Battery Notes entities only (maximum 3,650-day caller-selected range, default 365 days) and long-term statistics where metadata exists. Recorder values and aggregated statistics remain distinct `recorder_exact` / `statistics_inferred` samples. Battery Notes does not retain a full historical replacement archive, so earlier cycles are not fabricated.
- Added scoped test cases for discovery ranking, deterministic conversion, upstream provenance, partial/unmatched input, repeats, backup/restore, malformed payloads, manual values and history provenance. Updated migration and attribution documentation.
- Verification: local Ruff and `git diff --check` pass; GitHub Actions run `37223955627` passed Ruff and the full pytest suite. Native Windows pytest remains unavailable because the HA pytest plugin imports POSIX `fcntl`. No HA instance or Battery Notes data was modified.
- Next: Task 4, robust battery samples, replacement detection and per-device lifetime estimates.

## 2026-10-04 — Task 4 complete: battery lifecycle and estimator

- Added normalization for percentage/voltage/timestamps, stale and invalid readings, native-low transitions, low-level markers and bounded meaningful-sample checkpoints.
- Added reset-jump replacement candidates requiring user confirmation for replaceable cells; mains devices are excluded and rechargeable increases are represented as charging. Confirmed replacements close prior open cycles, store selected battery type/quantity and are idempotent.
- Added conservative median pairwise drain estimates with a minimum four valid samples over seven days. Estimates return a range and reason codes; sparse history returns unknown, completed same-device cycles allow only low-confidence fallback, and abnormal drain is compared to that device's past cycle rate. Coarse decile-only readings are marked low confidence.
- Added tests for invalid/stale and jittery readings, checkpoints, replacement/recharge separation, cycle close/repeat, sparse/flat/steep traces, history fallback and abnormal drain. Initial Linux run `37224310488` caught timestamp-only empty observations being returned as stale; commit `22dc504` added an entry guard, and run `37224408150` passed Ruff and the full pytest suite. Native Windows pytest remains blocked by HA's POSIX `fcntl` dependency.
- No entities or notifications were introduced in this task; estimator functions are pure and detailed output remains internal.
- Next: Task 5, generic availability and report-pattern learner.

## 2026-10-04 — Task 5 implementation: availability and report learner

- Added a per-device rolling report learner with median/p90/p95 intervals, jitter, pattern confidence and explicit event-only/irregular patterns.
- Added a separate health state engine: native unavailability wins; periodic profiles use per-device p90/p95 thresholds for degraded/stale/offline; startup grace and recovery stability are explicit; low-confidence/event-only silence remains unknown.
- Added filtered listeners for state changes and same-state `state_reported` events for selected sentinel IDs only. Initial states are read after listener registration to avoid missing the first report; unload unregisters both listeners and cancels debounced persistence. Last-seen/profile data is kept in a bounded rolling window and persisted after a short debounce.
- Updated the report-evidence ADR after checking HA Core 2026.9.4's actual helper signature: it has no `run_immediately` option, so Strážca subscribes first and seeds current states itself.
- Added tests for stable/jittery/irregular/event-only patterns, startup grace, per-device timeout transitions, native-availability precedence, recovery, allow-list scoping and unsubscribe. Initial CI run `37224839604` identified an overly loose irregularity cutoff and a stale test sample that actually crossed the offline threshold; tightened the relative jitter cutoff and moved the sample inside the stale window. Follow-up run `37225056438` passed Ruff and the full pytest suite. Native Windows pytest remains blocked by HA's POSIX `fcntl` dependency.
- Explicitly seeded current states after the Core 2026.9.4 filtered state/report listeners register; this is how immediate initialization is achieved with the available helper API.
- Next: Task 6, evidence scoring, shared-dependency grouping and cause revision history.

## 2026-10-04 — Task 6 implementation: evidence and incident clustering

- Added allow-listed timestamped evidence normalization and deterministic rule points for battery, connectivity, gateway/upstream, source integration and shared host/network causes. The response explicitly labels scores as evidence points, never probabilities; labels require at least 60 points and a 15-point margin or return `unknown`.
- Added explicit provider/config-entry dependency indexing and five-minute onset correlation. Integration name alone is not used as a physical dependency; shared clusters require at least three affected devices.
- Added incident open/update/close, deduplication by active affected-device set, parent/dependency links, acknowledgement/snooze fields and cause-revision history with inferred/user-confirmed provenance.
- Added labeled battery, individual RF, shared gateway, source integration, conflicting evidence, separate dependency, non-overlap and incident revision tests. Initial CI run `37225423791` found that the conflict fixture had stronger connectivity evidence and should correctly resolve to connectivity; changed it to a genuine low-battery versus coordinator-outage tie. Follow-up CI run `37225534978` passed Ruff and the full pytest suite. Native Windows pytest remains blocked by HA's POSIX `fcntl` dependency.

## 2026-10-04 — Task 7 implementation: Home Assistant entities, actions and events

- Resolved the inventory as `guardian_problem` + enum `guardian_status` for each tracked device, plus `battery_attention` for non-mains battery tracking. Entity attributes stay compact and omit detailed battery model, signal, estimator and history fields.
- Added helper-device linkage through the verified `async_entity_id_to_device` API and platform forwarding/unload for binary sensor and sensor entities.
- Added versioned, compact incident/recovery/battery-attention/battery-replaced events. Runtime health refresh opens/updates and closes incidents, groups correlated offline devices into one parent notification and suppresses child alert spam; repeated checks do not re-emit a continuing incident.
- Added registered actions `mark_battery_replaced`, `confirm_incident_cause`, `snooze_device` and `resume_device` with server-side validation; replacement is idempotent and event dispatch follows persistence. Battery source entity collection now feeds meaningful samples, an internal estimate and the single attention flag.
- Added English/Slovak entity names and Home Assistant service descriptions. Added tests for the three-entity cap, source-device linking, battery attention event, incident transition deduplication, all four actions and unload cleanup. Local Ruff/diff checks pass; GitHub Actions pending. Native Windows pytest remains blocked by HA's POSIX `fcntl` dependency.
- CI follow-up: run `37226802802` caught an old scaffold assertion expecting no entities; `37226961745` clarified that HA retains registry entries and publishes `unavailable` states on unload. During that repair, official HA guidance required service actions to register during integration setup and remain registered while no config entry is loaded. Runtime actions now follow that lifecycle; binary sensors no longer shadow HA's `group` API. Final Task 7 verification: GitHub Actions run `37227071067` passed Ruff and all 52 tests. Issue #8 closed.
- Next: Task 8, packaged side panel and authenticated internal WebSocket API.

## 2026-10-04 — Task 8 implementation: panel and internal API

- Ruling: package a dependency-free JavaScript custom element with the integration, register a self-hosted static resource and administrator-only custom panel, and authenticate/authorize all management WebSocket commands as admin. This keeps HACS updates atomic and avoids a remote/CDN dependency or independent Node build artifact.
- Added section-specific, allow-listed and paginated API responses for overview, battery catalogue/history/assignments, discovery, incidents and settings. Added admin-only commands for tracking/dismissing candidates, local model creation, per-device battery assignment, settings updates and Battery Notes preview/apply. Preview apply persists a separate pre-import backup before changing main storage.
- The bundled converted 2,330-model catalogue is seeded once into Strážca storage, preserving existing model rows/local edits. Selecting a candidate now adds its minimal HA entities and refreshes only the selected availability/battery subscriptions. Settings exposed in the panel are wired to the health grace/recovery and battery attention thresholds.
- Added a responsive Slovak UI with five tabs, search/pagination, accessible labels/focus order, explicit empty/unknown states, no raw HTML interpolation of dynamic values, signal recommendations without enabling them, plus local model creation and battery assignment. Added tests for serializer redaction, search/page bounds, local catalogue preservation, bundled data and live authenticated WebSocket tracking.
- Official design references: [custom panels](https://developers.home-assistant.io/docs/frontend/custom-ui/creating-custom-panels/), [WebSocket extensions](https://developers.home-assistant.io/docs/frontend/extending/websocket-api/) and [HA integration actions](https://developers.home-assistant.io/docs/dev_101_services/). Live browser/keyboard/viewport inspection against the actual HA instance remains for Task 9.
- Verification pending: Ruff, JavaScript syntax, API/integration tests and GitHub Actions. Native Windows pytest remains unavailable because HA's test plugin imports POSIX `fcntl`.
- CI run `37228679753` failed because the setup test harness leaves `hass.http` unset unless the required HA frontend dependency is declared. This affected every entry-setup test, not the API/feature assertions. Ruling: declare `frontend` as an integration dependency (it brings `http` and `websocket_api`); a sidebar panel needs these core services. Follow-up verification is pending.
- The next run `37228806311` showed that a hard `frontend` dependency also tries to import the HA frontend package, which is intentionally absent from this Python integration test environment. Revised ruling: depend on `http` only (required for the panel JS route); the frontend's built-in panel registry helper is usable independently, and opening the panel naturally requires the normal HA frontend.

## 2026-10-04 — Task 8/9 hardening follow-up

- Task 8 verification exposed an integration callback contract issue while exercising a newly tracked device over the real HA WebSocket test client. Runs `37228934427`, `37229131884`, `37229247727` and `37229379462` successively isolated entity-registration timing, cross-loop work in unmarked callbacks, and the HA 2026.9 DeviceRegistry collection API. Marked selected-report callbacks with HA's `@callback`, kept mutations on the HA event loop, waited for actual platform registration in the test, and changed device lookup/iteration to the supported `registry.async_get(id)` and `registry.devices` APIs. Latest CI after these changes is pending.
- Added the panel/API checks for safe field allow-lists, validated writes, pagination, unknown causes and live authenticated tracking. Static UI review covers five tabs, semantic tab controls, keyboard focus indicators, narrow-screen layout, empty/error states, migration preview and disabled signal recommendations; actual browser interaction still requires a disposable running HA instance.
- Task 9: added minimal HACS metadata, HACS validation plus Node JavaScript syntax and JSON parsing to CI, repository description/topics, an unreleased changelog and a first-release checklist. Source-code license remains an owner decision and is an explicit release blocker; the adjacent third-party data notice applies to the imported Battery Notes catalogue, not all project code.
- Audited shipped runtime paths: Battery Notes is accessed only through the optional migration module/API; filtered report listeners use explicitly selected entity IDs; no global `state_reported` listener or default signal entities are created. Labelled tests cap output to three entities per tracked battery device (two for mains) and exercise incident deduplication/cause scoring.
- Current limitation: CI is HA Core 2026.9.4 and covers setup, unload, migration/storage, actions/events and WebSocket behavior. A separate minimum-version matrix, clean HACS install/update, actual restart/backup-restore on HA, and browser/viewport pass are still required before a tagged release. No tag/release/deployment has been made.
- Final Task 8 feature verification: GitHub Actions run `37229725088`, commit `b0e3376`, Python job passed Ruff, Node syntax, both JSON files and all 63 pytest cases. HACS Action also passed metadata, topics, HACS JSON and integration manifest checks; it reports one repository-wide blocker: no source-code license. Task 8 issue #9 is complete; Task 9 remains open pending the owner's license choice and live release checks.
- Read-only environment probe reconfirmed the connected Home Assistant Core is `2026.9.4` and HACS is installed at `2.0.5`. No component files were installed or HA settings changed; actual panel rendering and HACS installation/update remain unverified.
