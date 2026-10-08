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
- Repository owner selected MIT on 2026-10-04. Added the repository-level `LICENSE`; the existing `THIRD_PARTY_DATA.md` continues to retain the separate upstream catalogue attribution/license notice. HACS CI rerun is pending.

### Task 9 CI follow-up

- GitHub Actions run `37231688845` passed the Python job: Ruff, JavaScript syntax, JSON validation and all 63 pytest cases.
- HACS Action still failed its license check because GitHub reports repository license metadata from the default `main` branch, where the MIT `LICENSE` has not been merged. The MIT file exists on `codex/sensor-guardian-mvp`; no changes were made directly to `main`. This is a branch/default-metadata condition, not a missing LICENSE on the development branch.
- No release tag was created. Clean HACS install/update and full live HA validation remain open.

## 2026-10-04 — documentation coverage and live first-run review

- Added a Slovak user guide for first run, candidate tracking, battery handling, one-time Battery Notes import, entities/events/actions, backup/upgrade and troubleshooting; added a developer guide for module boundaries, local/CI checks, storage/schema, observation constraints, WebSocket API and hotfix/release work.
- Added `DOCUMENTATION_POLICY.md` and a GitHub pull request template requiring docs/changelog review and verifiable CI/live evidence with every change. Linked the guides from README and distinguished shipped behavior from roadmap ideas.
- Reviewed the user's live panel read-only. The Devices tab presents discovery candidates; Overview showed zero tracked records. This is consistent with discovery requiring an explicit Track action. Candidate cards showed opaque registry IDs rather than friendly names; recorded as a user-facing limitation in FRONTEND/OPEN_QUESTIONS and README.
- Connector snapshots simultaneously reported zero config entries/entities despite returning the installed component files and the browser displaying the working panel. The visible browser state is the direct evidence used for the panel review; connector counts are not treated as proof that setup is absent.
- Recorded the requested compact battery table in [issue #11](https://github.com/denkz0ne/strazca-senzorov/issues/11) and the device table in [issue #12](https://github.com/denkz0ne/strazca-senzorov/issues/12), including readable identity/area, ZB/ZBT pattern, original HA integration, key diagnosis, filters and checkbox bulk tracking. No panel code was changed; `FRONTEND.md` labels them as future work.
- Extended issue #11 to extract/display optional `ZB###` and `ZBT###` identifiers from the readable device name (e.g. `zbt05-kupelna` → `ZBT05`), leaving the cell blank when neither pattern is present.
- Recorded the new-device sidebar badge, persistent pending discovery queue and automatic hiding of tracked/ignored devices in [issue #13](https://github.com/denkz0ne/strazca-senzorov/issues/13). No implementation was made.
- Recorded sticky section navigation and search while scrolling, including responsive and keyboard-accessibility checks, in [issue #14](https://github.com/denkz0ne/strazca-senzorov/issues/14). No implementation was made.
- No changes were made to Home Assistant. Documentation consistency, links, formatting and CI are pending this documentation commit.

## 2026-10-04 — Open UI issues #11–#14 implementation

- #11: Replaced per-device battery cards with a compact table, name-only ZB/ZBT identifier, live/latest sampled level, type/count, last replacement, attention/estimate, search/sort, narrow-screen scrolling and row-level assignment details.
- #12: Added HA display name/area/source integration metadata, separate integration and power/transport, compact Overview rows with expandable battery/incident evidence, selectable/filterable discovery rows and confirmed bulk tracking. Candidate rows show exact model matches and selected live readings; disabled signal recommendations remain off.
- #13: Added registry create/update/remove listeners and one idempotently updated native persistent-notification summary with exact pending count. Pending candidates derive from durable HA registries; tracked/ignored IDs are excluded and resolution uses existing storage. The supported HA custom-panel API has no numeric badge for an individual panel, so the notification badge is on HA's Notifications item and the Devices tab shows its candidate count. A new registry identity after re-pairing is treated as a new device.
- #14: Made the navigation/search row sticky, tab strip horizontally scrollable and data tables independently scrollable with sticky headers.
- Updated `FRONTEND.md`, `USER_GUIDE.md`, `OPEN_QUESTIONS.md`, `ROADMAP.md`, README and changelog. The user-owned HA instance was not modified.
- Verification: GitHub Actions PR run `37235438288` passed Ruff, JavaScript syntax, both JSON validations, all 73 pytest cases and HACS validation. A follow-up run removed the test-only async-mock warnings. Native Windows pytest remains blocked by HA's POSIX `fcntl` dependency.
- Discovery filter facets are calculated over the full candidate set, not only the current page; a regression test covers a second-page integration, area and availability value.
- Changes are committed as `d932575`, `46b987f`, and `e2f2df6` and pushed to PR [#15](https://github.com/denkz0ne/strazca-senzorov/pull/15). CI is green. Issues #11, #12, and #14 will close with the PR merge. Issue #13's exact per-panel badge criterion is blocked by HA's published API; the persistent notification workaround and exact count are implemented. Issue #10 still needs owner-run install/update/import-restore/restart/browser validation. No live HA update or release was performed.

## 2026-10-04 — HAOS log review and update hotfix

- Reviewed the user-provided HA Core 2026.9.4 log at `2026-10-04 23:32–23:35` local time. Strážca loaded its entities, but startup synchronously read `data/battery_models.json` on the event loop. HA also raised thread-safety errors for the delayed storage flush and 1-minute periodic callback; the rejected `async_create_task` calls left coroutines unawaited.
- Moved bundled model and Battery Notes preview catalogue reads to `hass.async_add_executor_job`. Marked the update, delayed flush and periodic callbacks `@callback` so HA runs them on the event loop. Added tests for executor thread use and HA callback classification.
- Other log messages are separate from Strážca: duplicate `utility_meter`/`frontend` YAML keys; an invalid archived package slug; translation placeholder failure in SmartThinQ; several network service timeouts; Watchman stale references; and normal custom-integration warnings. These were not changed.
- The hotfixes were merged to `main` in PR #15 (merge commit `5415d9e`). Main CI run `37237538284` passed Ruff, JavaScript/JSON checks, all 76 tests and HACS validation. The follow-up docs update records the merged state and owner update procedure.
- Live behavior remains unverified until the owner updates HA, checks its fresh log, and exercises migration/restore/restart and the real browser/viewport. Issue #10 remains open for those owner-run checks. No tag or release was created.

## 2026-10-05 — post-update HAOS log verification

- Reviewed `home-assistant_2026-10-04T22-00-19.929Z.log` (local log window 2026-10-04 23:57 through 2026-10-05 00:00; Home Assistant Core 2026.9.4). The log reaches setup of both `sensor_guardian.binary_sensor` and `sensor_guardian.sensor`.
- The previous Strážca faults are absent from this log: no blocking `battery_models.json` read, non-thread-safe `async_create_task`, or unawaited Strážca coroutine was reported. This is positive startup evidence after the update, not proof of migration/restore correctness or long-term runtime behavior.
- Unrelated configuration/integration errors remain, including duplicate `utility_meter`/`frontend` YAML keys, an invalid archived package slug, SmartThinQ translation placeholders, and an invalid legacy `notify.file` platform. REST/WLED/ESPHome and GeekMagic connection timeouts plus Watchman stale references also appear; none are attributed to Strážca.
- The user-provided post-update log was reviewed without making changes to HAOS. Issue #10 remains open for migration preview/apply/restore verification and live panel/browser review.

## 2026-10-07 — functional runtime repair (issue #18)

### Follow-up: unchanged live panel and wrong HACS default branch

- A subsequent owner screenshot still showed the old columns, Battery Notes runtime providers and missing percentages after a restart.
- Read-only HACS inspection established installed and available commit `fd0c0d8`, default/ref `codex/sensor-guardian-mvp`, and no pending update. GitHub repository metadata independently confirmed that same old default branch. The earlier instruction to update from main had not verified the actual repository default.
- Corrected the GitHub repository default branch to `main` and refreshed HACS repository information through its supported API. Re-read confirmed installed `fd0c0d8`, available `0df65e8`, default/ref `main`, pending update true. The latter commit includes runtime repair 0.1.1.
- Only repository settings and HACS metadata were changed. The owner still performs the actual integration download/restart; successful code CI and a refreshed update listing do not establish live deployment.

- Owner screenshot shows five tracked devices with no battery percentage and unknown health, including a mains MQTT socket assigned replaceable battery power. Read-only HA inspection confirms native ZHA battery states of 45 % and 100 %, device_class battery, and actual unavailable state on the mains socket. The enabled Guardian integration status does not establish functional correctness.
- Reproduced five faults before fixing them: GitHub run 37636729066 reported 5 failing regression tests and 76 passing prior tests. Numeric device_class battery was ranked as a binary low flag; localized metadata and helper source selection compounded the fault. Native mains voltage was misclassified and availability ignored actual source states.
- Native discovery now excludes Battery Notes/Guardian helpers, uses registry/device-class/unit metadata and selects primary source sentinels. Existing legacy bindings are repaired idempotently after a separate pre-repair backup; cycles, samples, assignments and explicit overrides are retained. Broken auto-recommended battery-only bindings are corrected, with editable tracked mode/power available in the panel.
- Source availability, unavailability, startup grace and recovery are handled without calling switch off an outage or equating a cached HA value to a radio packet. Cadence uses one source, diagnostics expose learning counts/gaps, and source corrections reset only the old availability profile. Recent last-known battery facts remain available for outage scoring; stale facts do not decide the cause.
- Added stable native outage/battery notifications, dismissal on recovery/replacement and a notification setting. Rapid drain can warn from a recent significant drop without inventing an ETA. Trends are scoped to the current replacement cycle and capped at 120 points for pairwise work.
- Fixed bulk per-device defaults, displayed percentage/signal directly, provided explicit recommended-signal activation and added 30-second refresh with preserved details/local dates. Local headless Chrome interaction checks passed; those checks now also run in GitHub CI with Chromium and simulated HA data. This is not a claim that the new version is already installed or visually verified on the owner's HAOS.
- Runtime evaluations and registry bursts are coalesced, scheduled storage flush is no longer postponed indefinitely by frequent reports, and unload saves pending data. Added redacted integration diagnostics. Version 0.1.1 identifies the fix; no release tag is created.
- Independent code review found mode-change notification cleanup and a mains actuator being omitted behind cached telemetry. Regression tests reproduced those cases; corrected primary availability selection and cleanup. A follow-up four-to-three group test reproduced a stale grouped notice and verified that replacement group links survive cleanup. Re-review has no remaining important findings in these changes.
- PR [#19](https://github.com/denkz0ne/strazca-senzorov/pull/19), reviewed implementation commit 7147d0b: [run 37642557225](https://github.com/denkz0ne/strazca-senzorov/actions/runs/37642557225) passed all 94 HA tests, HACS validation, Ruff/JS/JSON and Chromium interaction checks. Git push briefly returned server errors; exact source trees were uploaded through the Git API and verified identical locally before creating the PR. Owner-controlled HACS update and final live/migration/restore checks remain pending in issue #10.

## 2026-10-08 — prevention dashboard 0.2.0 (issue #21)

- Implemented the owner-approved design from PR #22: intervention/prevention/coverage overview, compact tracked devices/shared detail, actionable battery/availability alerts, reviewed bulk onboarding and inherited/global settings. Stock/catalogue are secondary utilities.
- Added actual 7/30/90-day charts, replacement cycle boundaries/history, dated stale values, prediction confidence/reasons, source overrides, mobile cards, sticky navigation and preserved drafts/focus. Versioned module URLs/custom-element registration and active backend/frontend versions expose old served assets.
- Store schema 1.2 adds signal observations/health transitions/stock and saves pre-upgrade backup. Optional bounded native Recorder history uses exact provenance and does not invent replacements. Per-device battery retention prevents another device's reports deleting quiet-device evidence.
- Fresh independent review identified timed snooze permanently acknowledging alerts, obsolete child notices, missing battery repetition, unlearned cadence labeled complete, prematurely completed onboarding and missing replacement display. Corrected all; re-review found no remaining important defects. Also handled older export migration, rule allow-list privacy, repeated pause/resume and stale pre-replacement percentage.
- Current implementation 96e3aa3: GitHub Actions [37723584803](https://github.com/denkz0ne/strazca-senzorov/actions/runs/37723584803) passed 110 HA tests, Ruff/JS/JSON, HACS 8 checks and Chromium interactions. Local Chrome interaction flow passed and produced dashboard/detail previews with simulated data.
- Updated README, architecture/data model, migration, availability, HA API, user/developer guides, frontend, roadmap, open questions, changelog, implementation ledger and owner update checklist. Delivery PR/main CI and HACS metadata are recorded below after completion.
- No live HA installation or restart was performed. Owner activation and live import/restore/browser checks remain issue #10. No stable tag/release is published.

### Delivery verification

- [PR #23](https://github.com/denkz0ne/strazca-senzorov/pull/23) merged as dc9d373 on 2026-10-08; issue #21 closed. [Main CI 37723915734](https://github.com/denkz0ne/strazca-senzorov/actions/runs/37723915734) passed python/HACS/frontend jobs.
- Refreshed HACS repository information only. Read-back confirms installed 7d1483a, available dc9d373 and pending_update true. GitHub default branch is main. Owner can now download the integration update, restart and verify backend/frontend 0.2.0.
- No HAOS download/restart or stable release/tag. Issue #10 retains live installation, migration/restore and actual browser/provider evidence. Documentation-only audit follows the tested merge without changing implementation.
