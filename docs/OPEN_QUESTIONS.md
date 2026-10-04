# Open questions

These are intentionally unresolved; the design should not imply they are settled.

## Identity and support

- Confirm public English name (`Sensor Guardian`) alongside Slovak display name.
- ~~Confirm HA domain.~~ `sensor_guardian` selected for the initial implementation; recheck the custom-integration ecosystem before first release.
- ~~Select HA minimum.~~ Target Core `2026.9.4`, initial support floor Core `2026.9`; run compatibility validation against this minimum and a current Core build before release.
- Decide whether first delivery targets HACS custom integration only and what frontend packaging/update method to use.

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

- Final minimal entity set: should `guardian_status` and `guardian_problem` both be created, or should one be optional?
- Final event/action names and payload stability/versioning?
- Which signal entity types can safely be enabled programmatically, and should Strážca only recommend or also offer an explicit enable button?
- Panel framework, localization scope and role/permission behavior?
- Should battery stock management be part of initial release or a later enhancement?
