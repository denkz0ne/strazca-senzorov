# ADR 0002: Source-device linking and report-time evidence

- Status: accepted for implementation
- Date: 2026-10-04
- Decision owners: project maintainer

## Entity-to-device linking

Strážca entities are helper entities attached to an existing source device. For an entity with a valid config entry and unique ID, resolve the source `DeviceEntry` with:

```python
from homeassistant.helpers.device import async_entity_id_to_device

device_entry = async_entity_id_to_device(hass, source_entity_id)
```

Pass the result to the Strážca entity and set `self.device_entry = device_entry`. If the source entity/device no longer resolves, leave `device_entry` as `None` and keep Strážca's own tracking record intact until the user decides what to do.

Do not call `device_registry.async_update_device(..., add_config_entry_id=...)` for the source device. Do not describe a source integration's device through Strážca `device_info`; both approaches attach Strážca's config entry to another integration's device. Each Strážca entity still needs a unique ID and must be added from its config entry.

Verified against the official helper-integration guidance and the Core 2026.9.4 `utility_meter` helper entity implementation.

## Report-time evidence

`State.last_reported` is updated for writes even when state and attributes are unchanged. `state_reported` has high volume. The observation collector will:

- track only selected sentinel entities or provider-owned entities for which report-time evidence is useful;
- use `hass.bus.async_listen(EVENT_STATE_REPORTED, callback, event_filter=..., run_immediately=True)` with a filter restricted to those entity IDs;
- avoid subscribing to every entity and avoid global event listeners;
- treat `last_reported` as evidence that a source entity integration wrote a state, not proof that the physical device transmitted over the radio at that exact time;
- use native availability and provider-specific evidence with greater weight where it is available;
- remove listeners when the config entry unloads and avoid raising incidents during startup grace.

Provider adapters may later supply a closer-to-transport last-seen signal. Generic `last_reported` alone cannot distinguish device silence from an integration that continues to publish cached state.

## Storage expectations

Use the typed, versioned `homeassistant.helpers.storage.Store` for integration-owned JSON-serializable records. The target Core includes the 2025.11 behavior change: serialization executes in the event loop by default; selecting executor-thread serialization is opt-in and requires thread-safe data access. Keep save payload creation event-loop-safe and avoid `serialize_in_event_loop=False` unless profiling justifies it and tests prove thread safety.

## Sources

- [Helper entity linking](https://developers.home-assistant.io/blog/2025/07/18/updated-pattern-for-helpers-linking-to-devices/)
- [State.last_reported and state_reported listener requirements](https://developers.home-assistant.io/blog/2024/03/20/state_reported_timestamp/)
- [Core 2026.9.4 helper entity source](https://github.com/home-assistant/core/blob/2026.9.4/homeassistant/components/utility_meter/select.py)
- [Storage serialization behavior](https://developers.home-assistant.io/blog/2025/11/25/storage-helper-opt-in-serialize-in-executor/)
