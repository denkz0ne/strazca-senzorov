"""Home Assistant sidebar panel registration."""

from pathlib import Path

from homeassistant.components import frontend
from homeassistant.components.http.server import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import DOMAIN, TITLE, VERSION


async def async_register_panel(hass: HomeAssistant) -> None:
    """Serve the bundled panel module and register its admin-only route."""
    panel_path = Path(__file__).parent / "www" / "panel.js"
    await hass.http.async_register_static_paths(
        [StaticPathConfig(f"/{DOMAIN}/panel.js", str(panel_path), cache_headers=False)]
    )
    frontend.async_register_built_in_panel(
        hass,
        component_name="custom",
        frontend_url_path=DOMAIN,
        sidebar_title=TITLE,
        sidebar_icon="mdi:lan-connect",
        require_admin=True,
        config={
            "_panel_custom": {
                "name": "sensor-guardian-panel",
                "js_url": f"/{DOMAIN}/panel.js?v={VERSION}",
            }
        },
        update=True,
    )
