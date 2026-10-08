# Frontend — prevention dashboard 0.2.0

The panel's primary purpose is preventing battery-device outages and explaining unavailable devices. Model data and stock are secondary settings utilities.

## Navigation and flows

| Section | Purpose |
| --- | --- |
| Prehľad | Unique-device counts, intervention, prevention, incomplete coverage, grouped outages and recent transitions |
| Zariadenia | Tracked-device search/filter/paging, readable names, HA area/provider, battery/signal, shared detail |
| Upozornenia | Active/closed battery and availability incidents, group membership, evidence, acknowledgment and timed snooze |
| Pridať zariadenia (count) | Pending native discovery → selection/choices → reviewed preview → revalidated apply → per-row outcome/retry |
| Nastavenia | Inherited/global rules, delivery policy, history, version/diagnostics, secondary stock/catalogue/migration utilities |

The sticky navigation/search stays accessible. Desktop uses compact tables; tracked devices use cards on mobile. All text is Slovak, generated through DOM textContent; no remote CDN, browser-stored credential or HTML rendering of HA strings.

Device detail includes actual 7/30/90-day SVG battery/voltage/signal series, availability transitions, replacement history, prediction reasons/confidence, diagnosis, mode/power and nullable rule overrides. Battery charts break at replacement boundaries and known gaps/outages. Initial availability in the chart is explicitly a last-known baseline. Signal daily averages are labeled. Physical packets are never inferred from cached HA state alone.

## Assets and state

`www/panel.js` manages route, query, paging, period, filters, selection and dirty drafts. View modules are in `www/frontend/`: ui, styles, charts, dashboard, devices, detail, alerts, onboarding and settings. `panel.py` serves both asset paths. Module URLs and the root custom-element tag are versioned (0.2.0), preventing an old browser registration from silently handling the new panel. Backend/frontend mismatch and stale evaluations are visible.

Thirty-second refresh skips active editing and onboarding/migration forms. Dirty drafts, focused fields and expanded source details survive deliberate data reloads. Async route results are discarded if superseded. Leaving dirty drafts asks before discarding.

## Contract and verification

Admin-only authenticated HA WebSocket endpoints provide bounded DTOs, native sources and permitted mutations. See [developer guide](DEVELOPER_GUIDE.md). Preview lasts 15 minutes; registry source changes block the batch. Receipt phases persist the selected signal enablement and permit completing interrupted operations. Explicit signal activation requires consent.

`tests/frontend/test_prevention_panel.cjs` serves the actual ES modules to Chromium with simulated HA DTOs and exercises navigation, details, preserved edits, acknowledgment, blocked/retried onboarding, stock, mobile width and an old cached custom-element registration. These are browser integration checks, not proof the owner's HA currently serves these assets. Owner checks are in [release checklist](RELEASE_CHECKLIST.md).
