const assert = require("node:assert/strict");
const fs = require("node:fs");
const http = require("node:http");
const path = require("node:path");
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || "playwright");

(async () => {
  const directory = path.dirname(path.resolve(process.argv[2]));
  const server = http.createServer((req, res) => {
    const pathname = new URL(req.url, "http://localhost").pathname;
    if (pathname === "/") {
      res.setHeader("content-type", "text/html; charset=utf-8");
      res.end('<style>body{margin:0;font:16px Arial;--primary-text-color:#17202a;--primary-background-color:#f5f7fa;--card-background-color:white;--divider-color:#ddd;--secondary-background-color:#edf2f6;--primary-color:#008eab;--secondary-text-color:#53687b;--error-color:#ba3030}</style><script type="module" src="/sensor_guardian/panel.js?v=0.2.0"></script>'); return;
    }
    const relative = pathname.replace(/^\/sensor_guardian\//, "");
    if (!/^(panel\.js|frontend\/[a-z-]+\.js)$/.test(relative) || !fs.existsSync(path.join(directory, relative))) { res.writeHead(404); res.end(); return; }
    res.setHeader("content-type", "text/javascript; charset=utf-8"); res.end(fs.readFileSync(path.join(directory, relative)));
  });
  await new Promise(resolve => server.listen(0, "127.0.0.1", resolve));
  const browser = await chromium.launch({ channel: process.env.PLAYWRIGHT_CHANNEL || undefined, headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1050 } });
    const errors = []; page.on("pageerror", error => errors.push(error.message));
    await page.goto(`http://127.0.0.1:${server.address().port}/`);
    await page.waitForFunction(() => customElements.get("sensor-guardian-panel"));
    await page.evaluate(() => {
      window.commands = []; window.confirm = () => true;
      const now = new Date().toISOString(), meta = { backend_version: "0.2.0", evaluated_at: now, collection_state: "running", schema_version: "1.2" };
      const battery = { device_id: "battery", name: "zb65.stmievac", area_name: "Chodba", source_integration: "zha", power_type: "replaceable_battery", tracking_mode: "battery_and_availability", health_state: "healthy", battery_level: 45, battery_type: "AAA", battery_quantity: 2, sample_count: 1, report_count: 1, span_days: 0, rules: {}, recommended_signal_entities: ["sensor.lqi"], signal_values: [], risk: { level: "learning", priority: 3, reasons: ["estimate_learning"] }, quality: { state: "incomplete", missing: ["estimate_learning"] }, estimate: { remaining_days_range: null, confidence: "none", reason_codes: ["insufficient_history"] } };
      const socket = { device_id: "socket", name: "Zásuvka SERVER", area_name: "Dom", source_integration: "mqtt", power_type: "mains", tracking_mode: "availability_only", health_state: "offline", battery_level: null, risk: { level: "critical", priority: 0, reasons: ["device_offline"] }, quality: { state: "complete", missing: [] }, estimate: { remaining_days_range: null }, signal_values: [] };
      const candidates = [
        { device_id: "new1", name: "Nový senzor", source_integration: "zha", power_type: "replaceable_battery", suggested_mode: "battery_and_availability", has_battery_data: true, entity_refs: { battery_level: "sensor.new_battery" }, recommended_signal_entities: ["sensor.new_lqi"] },
        { device_id: "new2", name: "Nová zásuvka", source_integration: "mqtt", power_type: "mains", suggested_mode: "availability_only", has_battery_data: false, entity_refs: {}, recommended_signal_entities: [] }
      ];
      const alert = { incident_id: "i1", device_ids: ["socket"], names: ["Zásuvka SERVER"], device_count: 1, cause: "unknown", evidence: [], health_state: "offline", opened_at: now, acknowledged: false };
      const settings = { low_battery_threshold: 20, startup_grace_minutes: 5, recovery_stability_minutes: 2, notifications_enabled: true, prevention_horizon_days: 14, retention_days: 365, quiet_start: "", quiet_end: "", notification_repeat_minutes: 0 };
      const stock = { battery_type: "AAA", on_hand: null, minimum: 2, installed_quantity: 2, used_quantity: 2, device_count: 1, suggested_reserve: 2, basis: "confirmed_replacements" };
      const panel = document.createElement("sensor-guardian-panel"); document.body.append(panel); let attempts = 0;
      panel.hass = { states: { "sensor.new_battery": { state: "70", attributes: { unit_of_measurement: "%" } } },
        callWS: async msg => {
          window.commands.push(msg); const name = msg.type.split("/")[1];
          if (name === "get_dashboard") return { meta, pending_count: 2, counts: { total: 2, offline: 1, attention: 1, prevention: 0, coverage: 1, healthy: 1 }, urgent: [socket], prevention: [], coverage: [battery], alerts: [alert], recent: [] };
          if (name === "get_devices") return { meta, items: [battery, socket], total: 2, has_more: false, filters: { areas: ["Chodba", "Dom"], integrations: ["mqtt", "zha"] } };
          if (name === "get_device_detail") return { meta, device: msg.device_id === "battery" ? battery : socket, series: { battery: [{ timestamp: now, value: 45 }], voltage: [], signal: [], availability: [] }, cycles: [], incidents: [alert], sources: { entity_refs: { battery_level: "sensor.battery" }, signals: [] }, inherited_rules: settings, source_choices: [], profile: {}, period_days: msg.days };
          if (name === "get_alerts") return { meta, items: [alert], total: 1, has_more: false };
          if (name === "acknowledge_alert") { alert.acknowledged = true; return { saved: true }; }
          if (name === "get_candidates") return { meta, items: candidates, total: candidates.length, has_more: false };
          if (name === "preview_tracking") return { preview_id: "reviewed", items: candidates.map(c => ({ ...c, tracking_mode: msg.choices.find(x => x.device_id === c.device_id)?.tracking_mode || c.suggested_mode, source_count: c.has_battery_data ? 1 : 0 })) };
          if (name === "apply_tracking") return ++attempts === 1 ? { applied: false, results: [{ name: "Nový senzor", status: "blocked" }, { name: "Nová zásuvka", status: "source_changed" }] } : { applied: true, results: candidates.map(c => ({ ...c, status: "tracked" })) };
          if (name === "get_settings") return { meta, settings, migration_count: 0 };
          if (name === "get_stock") return { items: [stock] };
          if (name === "save_stock") { Object.assign(stock, msg); return { saved: true }; }
          if (name === "update_device_rules") { battery.rules = msg.values; return { saved: true }; }
          if (["update_tracking", "save_settings", "set_tracking_active", "enable_signal_entities", "load_native_history"].includes(name)) return { saved: true };
          throw new Error("Unexpected command " + msg.type);
        }, callService: async (domain, name, data) => { window.commands.push({ type: domain + "/" + name, ...data }); return {}; }
      };
    });
    await page.getByRole("heading", { name: "Čo potrebuje zásah", exact: true }).waitFor();
    await page.getByRole("tab", { name: "Zariadenia", exact: true }).click();
    await page.getByRole("button", { name: "zb65.stmievac", exact: true }).click();
    await page.getByRole("heading", { name: "zb65.stmievac", exact: true }).waitFor();
    assert.equal(await page.getByText("45 %", { exact: true }).first().isVisible(), true);
    await page.getByLabel("Nízka batéria (%)").fill("17");
    await page.evaluate(() => document.querySelector("sensor-guardian-panel").autoRefresh());
    assert.equal(await page.getByLabel("Nízka batéria (%)").inputValue(), "17");
    await page.getByRole("button", { name: "Uložiť pravidlá", exact: true }).click();
    assert.equal(await page.evaluate(() => window.commands.find(c => c.type.endsWith("/update_device_rules")).values.low_battery_threshold), 17);
    await page.getByRole("tab", { name: "Upozornenia", exact: true }).click();
    await page.getByRole("button", { name: "Potvrdiť prečítanie", exact: true }).click();
    await page.getByRole("tab", { name: /^Pridať zariadenia/ }).click();
    await page.getByRole("checkbox", { name: "Vybrať Nový senzor", exact: true }).check();
    await page.getByRole("checkbox", { name: "Vybrať Nová zásuvka", exact: true }).check();
    await page.getByRole("button", { name: "Skontrolovať výber", exact: true }).click();
    await page.getByRole("button", { name: "Začať sledovať", exact: true }).click();
    await page.getByText("Sledovanie sa nezačalo", { exact: true }).waitFor();
    await page.getByRole("button", { name: "Znovu skontrolovať", exact: true }).click();
    await page.getByRole("button", { name: "Začať sledovať", exact: true }).click();
    await page.getByText("Sledovanie bolo zapnuté", { exact: true }).waitFor();
    const preview = await page.evaluate(() => window.commands.find(c => c.type.endsWith("/preview_tracking")));
    assert.equal(preview.choices.find(c => c.device_id === "new2").power_type, "mains");
    await page.getByRole("tab", { name: "Nastavenia", exact: true }).click();
    await page.getByRole("button", { name: "Batérie a zásoby", exact: true }).click();
    await page.getByLabel("Zásoba AAA").fill("8");
    await page.getByRole("button", { name: "Uložiť AAA", exact: true }).click();
    assert.equal(await page.evaluate(() => window.commands.find(c => c.type.endsWith("/save_stock")).on_hand), 8);
    await page.setViewportSize({ width: 390, height: 844 });
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), true);
    assert.deepEqual(errors, []);
    if (process.env.PANEL_SCREENSHOT) await page.screenshot({ path: process.env.PANEL_SCREENSHOT, fullPage: true });
    console.log("PASS: prevention dashboard, detail/form preservation, acknowledgment, blocked/retried onboarding, stock, mobile and module loading.");
  } finally { await browser.close(); await new Promise(resolve => server.close(resolve)); }
})().catch(error => { console.error(error); process.exit(1); });
