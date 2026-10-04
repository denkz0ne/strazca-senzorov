# Integration panel

The side panel is for detailed management and diagnosis; automations use the smaller HA entity/event interface.

## Tabs

1. **Overview** — tracked devices, area, health, source/transport, battery attention, last seen and active incident. Filters for problems, battery devices, offline/stale, protocol and area. Device detail drawer: health timeline, battery graph/cycle, incident history and explanation of current evidence. Do not surface temperature, occupancy or unrelated device measurements as Strážca-owned data.
2. **Batteries** — device battery assignments, battery type catalogue, replacement history, upcoming replacement needs and optional household stock. Adding an unknown model should require minimal input: review prefilled manufacturer/model/source and select battery type; quantity defaults to one and is editable. Applying the choice to all matching models is optional and explicit.
3. **Devices** — discovery recommendations with match evidence and proposed tracking mode; accept, edit, ignore and undo. Distinguish battery-powered, rechargeable and mains-powered devices. Signal entities that could improve diagnosis can be recommended for enabling here.
4. **Incidents** — grouped and individual incident timeline, current/previous cause, confidence/evidence, acknowledgement, confirmation/correction and recovery.
5. **Settings** — notification policy, startup grace, stale/offline thresholds, sampling, model catalogue management, import status, provider support and diagnostics.

Tabs may be combined or reordered after usability work; these five areas capture current needs. Panel remains useful with generic provider data and must label unsupported diagnostics clearly.

## Interaction principles

- Explain recommendations and cause estimates in ordinary language.
- Show approximate ranges and confidence for lifetime estimates; no false precision.
- Keep unknown and insufficient history visible.
- Make model/library edits local and reversible; preserve per-device overrides.
- Confirm destructive resets and provide export/backup for migration and data reset.
