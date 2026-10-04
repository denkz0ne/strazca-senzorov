"""Tests for the global Sensor Guardian config entry."""

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import EVENT_STATE_REPORTED
from homeassistant.core import is_callback
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
from homeassistant.loader import async_get_custom_components
from pytest_homeassistant_custom_component.common import MockConfigEntry

DOMAIN = "sensor_guardian"


async def test_custom_component_is_discovered(hass):
    """The Home Assistant loader finds the packaged custom integration."""
    integrations = await async_get_custom_components(hass)
    assert DOMAIN in integrations


async def test_user_flow_creates_the_global_entry(hass):
    """The user flow creates exactly one titled global config entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "user"},
    )

    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={}
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Strážca senzorov"
    assert result["data"] == {}
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1


async def test_user_flow_aborts_if_an_entry_already_exists(hass):
    """A second global config entry is rejected before another is created."""
    existing = MockConfigEntry(domain=DOMAIN, data={}, unique_id="global")
    existing.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "user"},
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1


async def test_empty_entry_sets_up_and_unloads_without_entities(hass):
    """The empty scaffold unloads cleanly and registers no product entities."""
    entry = MockConfigEntry(domain=DOMAIN, data={}, unique_id="global")
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id) == []
    assert hass.bus.async_listeners().get(EVENT_STATE_REPORTED, 0) == 0
    assert hass.services.has_service(DOMAIN, "mark_battery_replaced")
    assert hass.services.has_service(DOMAIN, "confirm_incident_cause")
    panel = hass.data["frontend_panels"][DOMAIN].to_response()
    assert panel["component_name"] == "custom"
    assert panel["require_admin"] is True
    assert len(hass.data[DOMAIN][entry.entry_id]["data"]["models"]) == 2330

    assert await hass.config_entries.async_unload(entry.entry_id)
    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_timer_callbacks_are_event_loop_safe(hass, monkeypatch):
    import custom_components.sensor_guardian as integration

    callbacks = {}

    def capture_call_later(_hass, _delay, action):
        callbacks["flush"] = action
        return lambda: None

    def capture_interval(_hass, action, _interval):
        callbacks["periodic"] = action
        return lambda: None

    monkeypatch.setattr(integration, "async_call_later", capture_call_later)
    monkeypatch.setattr(integration, "async_track_time_interval", capture_interval)

    entry = MockConfigEntry(domain=DOMAIN, data={}, unique_id="timer-test")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)

    runtime = hass.data[DOMAIN][entry.entry_id]
    runtime["schedule_save"]()

    assert is_callback(callbacks["flush"])
    assert is_callback(callbacks["periodic"])
    await hass.config_entries.async_unload(entry.entry_id)
