# ADR 0001: Home Assistant compatibility floor

- Status: accepted for the first implementation
- Date: 2026-10-04
- Decision owners: project maintainer

## Context

The connected Home Assistant configuration reports Core version **2026.9.4** through `/config/.HA_VERSION`. The read-only snapshot API did not expose the version; reading the version file supplied the missing value. The implementation needs modern helper-entity device linking and an explicit custom integration manifest.

## Decision

- Target the user's current Home Assistant Core **2026.9.4**.
- Set the initial supported minimum to **Home Assistant Core 2026.9**. Recheck this floor at release time; do not claim support for earlier releases without a compatibility run.
- Treat Home Assistant OS version as outside the compatibility contract; the integration depends on Core APIs.
- Use the custom integration domain `sensor_guardian`. A GitHub code search of Home Assistant Core returned no use of this domain at decision time; this is a Core-domain check, not a claim of global uniqueness across custom integrations.
- Use one global config entry (`single_config_entry: true`) because this integration observes the whole HA device registry.
- Declare `integration_type: "helper"` and `iot_class: "calculated"`: the integration observes HA entities and calculates health/battery information without communicating directly with devices.
- Include the custom integration's required version, config flow metadata and no runtime dependency on Battery Notes.

## Consequences

The custom integration can use Core 2026.9's helper-linking API and storage behavior directly. Compatibility testing must include Core 2026.9.4 and a current Core build before release. If support below 2026.9 becomes necessary, revisit helper-device linking and event-listener compatibility explicitly.

## Sources

- Target instance file: `/config/.HA_VERSION` → `2026.9.4` (read-only HA tool).
- [Integration manifest](https://developers.home-assistant.io/docs/creating_integration_manifest/) — custom version, `integration_type`, config flow and single-entry fields.
- [Helper integrations linking to source devices](https://developers.home-assistant.io/blog/2025/07/18/updated-pattern-for-helpers-linking-to-devices/) — previous config-entry attachment ceases to work in Core 2026.8.
- [Home Assistant Core 2026.9.4 utility meter helper entity](https://github.com/home-assistant/core/blob/2026.9.4/homeassistant/components/utility_meter/select.py) — imports `async_entity_id_to_device` from `homeassistant.helpers.device` and assigns the returned device to `self.device_entry`.
