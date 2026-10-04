# Open questions

These are intentionally unresolved; the design should not imply they are settled.

## Identity and support

- Confirm public English name (`Sensor Guardian`) alongside Slovak display name.
- ~~Confirm HA domain.~~ `sensor_guardian` selected for the initial implementation; recheck the custom-integration ecosystem before first release.
- ~~Select HA minimum.~~ Target Core `2026.9.4`, initial support floor Core `2026.9`; run compatibility validation against this minimum and a current Core build before release.
- First delivery targets HACS custom integration packaging; the panel is self-hosted in the integration folder with no runtime CDN/build dependency. Live HACS install/update still needs release validation.

## Data and migration

- Which Battery Notes library snapshot/release should be bundled and converted?
- Which exact installed Battery Notes version and storage keys/entities are present in the user's HA?
- What is the migration source precedence and how much Recorder/long-term statistics history is actually available?
- Should Battery Notes catalogue updates be copied manually by maintainers later, or should Strážca's bundled catalogue remain frozen except for project releases? Runtime synchronization is out of scope.
- Which fields need export/import and user-visible deletion/retention controls?

## Availability and diagnosis

- ~~Which report-time API is supported?~~ Use filtered `state_reported` with immediate initialization only for selected entities; verify load and physical-device interpretation with provider adapters.
- How to choose sentinel entities per integration without missing silent reports or processing noisy entities?
- Initial stale/offline multipliers, startup grace and recovery stability window?
- Which dependencies can each provider expose (coordinator, AP, gateway, config entry)?
- How should score/confidence be calibrated; what minimum labeled incident set is required before presenting numeric confidence?
- Which transports/providers are first-class in MVP based on user's actual installation?

## Battery estimator

- Minimum sample count/time span before showing an ETA?
- What counts as “replace soon” and how is user preference configurable?
- How to normalize battery percentage across devices with coarse/voltage-derived reporting?
- How should temperature, brand, chemistry and model-cohort data influence estimates, if at all?
- How are rechargeable batteries and devices with non-replaceable batteries represented in MVP?

## Home Assistant and panel

- ~~Final minimal entity set.~~ Both `guardian_status` and `guardian_problem` are in the initial automation API; `battery_attention` is battery-only.
- ~~Event/action names and payload stability.~~ Initial names and payload version 1 are documented in `docs/HOME_ASSISTANT.md`.
- ~~Signal entity enabling policy.~~ Recommend useful disabled signal entities; do not enable automatically.
- ~~Panel framework and role behavior.~~ Self-hosted custom panel, authenticated WebSocket API, administrator-only in the MVP. First UI is Slovak; broader localization can follow.
- Should battery stock management be part of initial release or a later enhancement?
- Device-list identity, bulk selection/filters and original integration display are tracked in [#12 — device list](https://github.com/denkz0ne/strazca-senzorov/issues/12). Show friendly name, HA area, and `ZB###`/`ZBT###` only if present in the name; otherwise leave the ID cell blank. Current discovery cards can expose opaque registry IDs, so readable identification is a release usability requirement. The Overview must show the source integration separately from power/transport.
