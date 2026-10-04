from pathlib import Path


def test_panel_asset_is_self_hosted_and_contains_all_product_tabs():
    panel_path = (
        Path(__file__).parents[1]
        / "custom_components"
        / "sensor_guardian"
        / "www"
        / "panel.js"
    )
    panel = panel_path.read_text(encoding="utf-8")

    assert "sensor-guardian-panel" in panel
    for section in ("overview", "batteries", "devices", "incidents", "settings"):
        assert f'data-section="{section}"' in panel
    assert "sensor_guardian/get_data" in panel
    assert "unpkg.com" not in panel
    assert "cdn.jsdelivr.net" not in panel
