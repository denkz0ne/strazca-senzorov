# Prevention UI implementation plan

> **For agentic workers:** Use superpowers:executing-plans inline. User approved the written design and authorized work; execute all tasks and maintain this ledger without intermediate approval requests.

**Goal:** Deliver a functioning prevention dashboard, device/history detail, actionable alerts, guided onboarding and coherent settings with secondary battery stock.

**Architecture:** Preserve existing HA entities/actions and native source selection. Add pure analytics DTOs and persistent bounded observations, expose admin WS commands, and replace the single renderer with self-hosted view modules.

**Tech Stack:** HA Core 2026.9.4/Python 3.14, HA Store schema 1.2, native JavaScript custom elements, local SVG charts, pytest and Chromium interactions.

**Spec:** ../specs/2026-10-07-prevention-first-ui-design.md (approved by owner).

## Global constraints

- Slovak labels, HA theme, compact desktop lists, usable narrow screens and keyboard focus.
- Native device observations only; Battery Notes migration only; no implicit signal enabling.
- Preserve tracked IDs/history/user choices and minimal HA entities.
- Missing data and low confidence remain visible; cached HA writes are not physical packets.
- Owner controls HAOS install/restart. GitHub default main and installed-version evidence are required.

## Review focus

- Empty/partial observations, invalid values and null percentages cannot appear as zero or healthy.
- Overlapping/grouped outages and changing members must not inflate summaries or produce stale notices.
- Concurrent data refresh and editing must preserve forms, selection, routes and focus.
- Bulk add/retry must identify partial outcomes and never duplicate records.
- Old Store payloads, unavailable Recorder and provider changes must preserve user history.

## Task 1 — Persistent evidence and analytics contract

Files: models.py, migrations.py, storage.py, new history.py/analytics.py, runtime.py, __init__.py, tests/test_prevention_analytics.py and tests/test_observations.py.

- [ ] Write failing tests for global unique-device counts, unknown data, quality/risk, charts, history retention and preserved schema upgrade.
- [ ] Observe failure on CI; implement observations (hourly signal checkpoints + changes, availability transitions) and pure sorted DTOs.
- [ ] Implement bounded optional native Recorder history fill; distinguish exact history from current/restored observation and tolerate missing Recorder.
- [ ] Verify current-cycle estimates, historical signal trends, stable grouping and evidence ages; commit.

## Task 2 — Admin operations and settings

Files: new prevention_api.py/onboarding.py, websocket_api.py, services.py, tests/test_prevention_api.py.

- [ ] Test admin authorization, filtered/global pagination, detail series and version metadata.
- [ ] Add dashboard/devices/detail/alerts/settings/stock endpoints without breaking legacy get_data.
- [ ] Add preview/apply onboarding, ID-based idempotence and per-item outcomes; refuse changed native sources before writes.
- [ ] Add per-device rule overrides, acknowledgment/pause/resume, settings, stock and export diagnostics; verify persistence and lifecycle.

## Task 3 — Modular prevention frontend

Files: www/panel.js, www/frontend/*.js, panel.py, tests/frontend/test_runtime_panel.cjs.

- [ ] Write failing browser scenarios for prevention navigation, detail/charts, partial onboarding, forms, alerts, settings and stock.
- [ ] Implement shared accessible DOM/theme/components and shell/version checks.
- [ ] Implement dashboard, device list/detail, alerts, onboarding and settings/secondary stock views against the real contract.
- [ ] Preserve selection/forms across refresh, show network/errors/stale data, paginate and restore route/focus.
- [ ] Verify DOM safety, keyboard, mobile widths and no phantom 0 %; commit.

## Task 4 — Regression, review and delivery

- [ ] Full pytest/HACS/Chromium checks and source/API/UI end-to-end regressions.
- [ ] Fresh-context branch review, correct important findings, and rerun affected checks.
- [ ] Version 0.2.0, docs/changelog/progress/contracts/schema/update notes; merge reviewed PR.
- [ ] Verify main CI and actual HACS update metadata. Live installation remains owner-controlled.

## Ledger

- Start: approved design merged in PR #22. Base main 5990566.
- Ruling: execute inline following explicit user instruction to work; design approval covers the requested scope. No additional routine approval gates.
- Ruling: device catalogue stays a secondary migration/model utility; stock statistics use tracked assignments and confirmed replacement cycles.
