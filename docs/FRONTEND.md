# Integration panel

The side panel is for detailed management and diagnosis; automations use the smaller HA entity/event interface.

## Tabs

1. **Overview** — tracked devices, area, health, source/transport, battery attention, last seen and active incident. Filters for problems, battery devices, offline/stale, protocol and area. Device detail drawer: health timeline, battery graph/cycle, incident history and explanation of current evidence. Do not surface temperature, occupancy or unrelated device measurements as Strážca-owned data.
2. **Batteries** — device battery assignments, battery type catalogue, replacement history, upcoming replacement needs and optional household stock. Adding an unknown model should require minimal input: review prefilled manufacturer/model/source and select battery type; quantity defaults to one and is editable. Applying the choice to all matching models is optional and explicit.
3. **Devices** — discovery recommendations with match evidence and proposed tracking mode; accept, edit, ignore and undo. Distinguish battery-powered, rechargeable and mains-powered devices. Signal entities that could improve diagnosis can be recommended for enabling here.
4. **Incidents** — grouped and individual incident timeline, current/previous cause, confidence/evidence, acknowledgement, confirmation/correction and recovery.
5. **Settings** — notification policy, startup grace, stale/offline thresholds, sampling, model catalogue management, import status, provider support and diagnostics.

Tabs may be combined or reordered after usability work; these five areas capture current needs. Panel remains useful with generic provider data and must label unsupported diagnostics clearly.

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
