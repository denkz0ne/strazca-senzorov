import json
import re
from pathlib import Path

from pytest_homeassistant_custom_component.common import MockConfigEntry

WWW = Path(__file__).parents[1] / "custom_components" / "sensor_guardian" / "www"


def test_self_hosted_module_graph_uses_the_manifest_cache_version():
    version = json.loads((WWW.parent / "manifest.json").read_text(encoding="utf-8"))[
        "version"
    ]
    panel = (WWW / "panel.js").read_text(encoding="utf-8")
    assert "sensor-guardian-panel" in panel
    assert "customElements.get(PANEL_TAG)" in panel
    sources = [panel] + [
        path.read_text(encoding="utf-8") for path in (WWW / "frontend").glob("*.js")
    ]
    for source in sources:
        assert "unpkg.com" not in source
        assert "cdn.jsdelivr.net" not in source
        for filename, imported_version in re.findall(
            r'from "(\./[^"?]+)\?v=([^"]+)"', source
        ):
            assert imported_version == version
            assert filename.endswith(".js")
    assert f'UI_VERSION = "{version}"' in sources[1] or any(
        f'UI_VERSION = "{version}"' in source for source in sources
    )
    for module in (
        "ui",
        "styles",
        "dashboard",
        "devices",
        "detail",
        "charts",
        "alerts",
        "onboarding",
        "settings",
    ):
        assert (WWW / "frontend" / f"{module}.js").is_file()


async def test_frontend_modules_are_served_by_the_packaged_http_route(
    hass, hass_client
):
    entry = MockConfigEntry(domain="sensor_guardian", data={}, unique_id="global")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    client = await hass_client()
    response = await client.get("/sensor_guardian/frontend/ui.js")
    assert response.status == 200
    assert 'UI_VERSION = "0.2.0"' in await response.text()
    panel = hass.data["frontend_panels"]["sensor_guardian"].to_response()
    assert panel["config"]["_panel_custom"]["name"] == "sensor-guardian-panel-0-2-0"
    await hass.config_entries.async_unload(entry.entry_id)
