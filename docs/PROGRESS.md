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
