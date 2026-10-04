"""Configuration flow for Sensor Guardian."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN, TITLE


class SensorGuardianConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Create the single global Sensor Guardian entry."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Set up the integration without requiring configuration."""
        await self.async_set_unique_id("global")
        self._abort_if_unique_id_configured()

        if user_input is not None:
            return self.async_create_entry(title=TITLE, data={})

        return self.async_show_form(step_id="user", data_schema=vol.Schema({}))
