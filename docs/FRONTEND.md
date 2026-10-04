# Integration panel

The side panel is for detailed management and diagnosis; automations use the smaller HA entity/event interface.

## Tabs

1. **Overview** — tracked devices, area, health, source/transport, battery attention, last seen and active incident. Filters for problems, battery devices, offline/stale, protocol and area. Device detail drawer: health timeline, battery graph/cycle, incident history and explanation of current evidence. Do not surface temperature, occupancy or unrelated device measurements as Strážca-owned data.
2. **Batteries** — device battery assignments, battery type catalogue, replacement history, upcoming replacement needs and optional household stock. Adding an unknown model should require minimal input: review prefilled manufacturer/model/source and select battery type; quantity defaults to one and is editable. Applying the choice to all matching models is optional and explicit.
3. **Devices** — discovery recommendations with match evidence and proposed tracking mode; accept, edit, ignore and undo. Distinguish battery-powered, rechargeable and mains-powered devices. Signal entities that could improve diagnosis can be recommended for enabling here.
4. **Incidents** — grouped and individual incident timeline, current/previous cause, confidence/evidence, acknowledgement, confirmation/correction and recovery.
5. **Settings** — notification policy, startup grace, stale/offline thresholds, sampling, model catalogue management, import status, provider support and diagnostics.

The implemented panel has these five tabs. Battery assignments and tracked battery devices use compact tables; discovery candidates use a selectable, filterable table. Unsupported registry or sensor data stays blank/unknown rather than inferred. Panel remains useful with generic provider data and labels unsupported diagnostics clearly.

## Observed current limitations

- The **Devices** discovery tab uses the HA device name, area, and source integration when available. Its pending notice uses the native Home Assistant notification badge (one persistent summary); custom panels have no supported per-panel sidebar counter.
- Overview and Incidents are empty until the user explicitly tracks candidates and incidents occur; discovery by itself does not create tracked records.
- The visible panel is a first usable management surface, not the final detailed analytics dashboard. Do not document planned controls as shipped until they appear in code and pass UI review.

## Compact lists and discovery

Issues [#11](https://github.com/denkz0ne/strazca-senzorov/issues/11) to [#13](https://github.com/denkz0ne/strazca-senzorov/issues/13) define the compact batteries/devices tables and discovery queue.

The section navigation and search row are sticky during panel scrolling; tables have their own horizontal scrolling area and sticky column headers. Tab buttons remain horizontally scrollable on narrow screens.

The **Batteries** table uses one compact row per tracked battery device and shows readable device name, the optional `ZB###`/`ZBT###` identifier parsed from the name, battery type/quantity, current level, last replacement, concise attention state and remaining-life estimate only when supported by enough history. An unrecognized identifier stays blank. `zbt05-kupelna` displays `ZBT05`. Search and sort cover useful fields; assignment controls are in row details.

The **Devices** list uses the HA display name and assigned area, plus a `ZB###` or `ZBT###` identifier only when present in the name. It shows original integration separately from power/transport, source battery values and reasons, and a prefilled battery model when an exact manufacturer/model match exists. Rows have individual tracking/power choices and checkboxes for confirmed bulk tracking. Filters cover integration, observed battery data, area and native availability. Missing values remain blank/unknown; disabled signal entities are never enabled automatically.

The **Overview** table shows the original HA integration and area for every tracked device, with battery and incident evidence in each row's expandable details.

Discovery derives its pending queue from the persistent HA device/entity registries and stored ignored IDs, so restart/reload does not duplicate candidates. A single actionable persistent notification updates on registry create/update/remove events and shows the exact number of candidates. Home Assistant's supported custom-panel API exposes no per-panel numeric sidebar badge; its native Notifications item shows one badge for this summary notification. The Devices tab also includes its current pending count. A device is never tracked without the user's explicit choice. Re-pairing with a new registry ID is treated as a new candidate; ignored IDs do not suppress a distinct new registry identity.

## MVP packaging and API

The MVP panel is a self-hosted, dependency-free JavaScript custom element in
`custom_components/sensor_guardian/www/panel.js`. `panel.py` registers it as a
Home Assistant custom panel and serves the packaged file from the integration;
no external script CDN or separate Node build step is required. HACS installs and
updates the integration directory as one unit.

The panel is administrator-only. It uses authenticated Home Assistant WebSocket
commands and never keeps durable state in the browser. `websocket_api.py`
provides bounded pages for overview, model catalogue/history, discovery,
incidents and settings. API serializers use per-section field allow-lists;
overview omits battery type, entity references and signal details. Settings and
all write commands validate IDs, page sizes and values.

Write operations cover tracking/dismissing discovery candidates, adding a local
battery-model record, assigning battery type/quantity per device, updating the
initial supported settings, and previewing/applying the one-time Battery Notes
import. Import apply stores a separate pre-import backup first. Replacement,
cause confirmation, snooze and resume use the same Home Assistant actions exposed
to automations. Discovery only recommends disabled signal entities; it does not
enable them.

The first UI release is Slovak, uses native keyboard focus order and semantic
tab/button/input labels, and adapts to narrow viewports. Unknown cause remains
visible as “neznáme”; empty catalogues and candidate/incident lists have explicit
messages. Interaction and layout still need a live Home Assistant browser check
during release hardening.

The current `hacs.json` declares the display name. It does not certify that an
install or update has been exercised by HACS; the first-release checklist
requires a clean install/update and a browser check on a disposable HA instance.

## Interaction principles

- Explain recommendations and cause estimates in ordinary language.
- Show approximate ranges and confidence for lifetime estimates; no false precision.
- Keep unknown and insufficient history visible.
- Make model/library edits local and reversible; preserve per-device overrides.
- Confirm destructive resets and provide export/backup for migration and data reset.
