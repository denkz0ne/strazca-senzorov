const assert = require("node:assert/strict");
const path = require("node:path");
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || "playwright");

(async () => {
  const browser = await chromium.launch({ channel: process.env.PLAYWRIGHT_CHANNEL || undefined, headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1050 } });
  await page.setContent('<style>body{font:16px Arial;--primary-text-color:#17202a;--primary-background-color:#fafafa;--card-background-color:white;--divider-color:#ddd;--secondary-background-color:#eee;--primary-color:#009ac0;--secondary-text-color:#52677a}</style>');
  await page.addScriptTag({ path: path.resolve(process.argv[2]) });
  await page.evaluate(() => {
    window.commands = [];
    window.confirm = () => true;
    const records = [
      { device_id: "battery", name: "zb65.stmievac", identifier: "ZB65", area_name: "Chodba",
        source_integration: "zha", power_type: "replaceable_battery", suggested_mode: "battery_and_availability",
        tracking_mode: "battery_and_availability", health_state: "healthy", battery_level: 45,
        battery_type: "AAA", battery_quantity: 2, last_reported_at: "2026-10-06T21:48:30Z",
        sample_count: 1, report_count: 1, recommended_signal_entities: ["sensor.lqi"],
        entity_refs: { battery_level: "sensor.battery" }, confidence: "high", has_battery_data: true },
      { device_id: "socket", name: "Zásuvka SERVER", area_name: "Dom", source_integration: "mqtt",
        suggested_mode: "availability_only", tracking_mode: "availability_only", power_type: "mains",
        health_state: "offline", confidence: "medium", has_battery_data: false, reasons: [] }
    ];
    const panel = document.createElement("sensor-guardian-panel");
    document.body.append(panel);
    panel.hass = {
      states: { "sensor.battery": { state: "45", attributes: { unit_of_measurement: "%" } } },
      callWS: async (message) => {
        window.commands.push(message);
        if (message.type === "sensor_guardian/get_data") return {
          section: message.section, items: records, total: records.length, has_more: false,
          facets: { integrations: ["zha", "mqtt"], areas: ["Chodba", "Dom"], availability: ["unknown"] }
        };
        return { updated: true, tracked: true };
      },
      callService: async () => ({})
    };
  });
  await page.getByRole("columnheader", { name: "Batéria", exact: true }).waitFor();
  assert.equal(await page.getByRole("cell", { name: "45 %", exact: true }).isVisible(), true);
  await page.getByRole("tab", { name: "Zariadenia" }).click();
  await page.getByRole("checkbox", { name: "Vybrať zb65.stmievac", exact: true }).check();
  await page.getByRole("checkbox", { name: "Vybrať Zásuvka SERVER", exact: true }).check();
  await page.getByRole("button", { name: "Sledovať vybrané (2)", exact: true }).click();
  await page.waitForFunction(() => window.commands.filter(c => c.type === "sensor_guardian/track_device").length === 2);
  const tracked = await page.evaluate(() => window.commands.filter(c => c.type === "sensor_guardian/track_device"));
  assert.equal(tracked[0].tracking_mode, "battery_and_availability");
  assert.equal(tracked[0].power_type, "replaceable_battery");
  assert.equal(tracked[1].tracking_mode, "availability_only");
  assert.equal(tracked[1].power_type, "mains");
  await page.getByRole("tab", { name: "Prehľad" }).click();
  await page.locator("summary").first().click();
  await page.getByRole("combobox", { name: "Režim sledovaného zariadenia" }).first().selectOption("battery_only");
  await page.getByRole("button", { name: "Uložiť sledovanie" }).first().click();
  assert.equal(await page.evaluate(() => window.commands.find(c => c.type === "sensor_guardian/update_tracking").tracking_mode), "battery_only");
  await page.getByRole("button", { name: "Zapnúť odporúčané signálové entity" }).click();
  assert.equal(await page.evaluate(() => window.commands.find(c => c.type === "sensor_guardian/enable_signal_entities").device_id), "battery");
  await page.setViewportSize({ width: 390, height: 844 });
  assert.equal(await page.getByRole("tab", { name: "Prehľad" }).isVisible(), true);
  await browser.close();
  console.log("PASS: native percentage display, per-device bulk defaults, tracked-mode edit, explicit signal enable, narrow layout.");
})().catch(error => { console.error(error); process.exit(1); });

