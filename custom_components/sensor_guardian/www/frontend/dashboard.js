import { ago, badge, btn, card, el, empty, eta, label, percent, reason } from "./ui.js?v=0.2.0";

function list(app, title, description, rows, fallback) {
  const section = card(title, description);
  if (!rows.length) section.append(empty(fallback));
  for (const device of rows) {
    const line = el("div", null, "device-line"), info = el("div", null, "device-info"), status = el("div");
    info.append(btn(device.name || "Sledované zariadenie", () => app.go("detail", { id: device.device_id }), "link"),
      el("p", [device.area_name, device.source_integration].filter(Boolean).join(" · "), "muted"),
      el("p", (device.risk?.reasons || []).map(reason).join(" ") || label(device.health_state), "small"));
    status.append(badge(label(device.risk?.level), device.risk?.level));
    if (device.power_type !== "mains") status.append(el("p", `${percent(device.battery_level)} · ${eta(device.estimate)}`, "muted"));
    line.append(info, status); section.append(line);
  }
  return section;
}
export function dashboardView(app, data) {
  const page = el("div");
  page.append(el("p", "Prevencia výpadkov a stav sledovaných zariadení", "muted"));
  const metrics = el("div", null, "metrics");
  for (const [title, key, tone, caption] of [
    ["Nedostupné", "offline", "critical", "aktuálny stav v HA"],
    ["Potrebujú zásah", "attention", "attention", "dostupnosť alebo batéria"],
    ["Preventívne odporúčania", "prevention", "watch", "podľa pravidiel jednotlivých zariadení"],
    ["Chýbajúce údaje", "coverage", "learning", "učenie a pokrytie meraní"],
  ]) {
    const metric = btn("", () => app.go("devices", { filter: key === "offline" ? "offline" : key === "attention" ? "attention" : key === "prevention" ? "prevention" : "coverage" }), `metric ${tone}`);
    metric.append(el("span", title), el("strong", data.counts[key]), el("span", caption, "muted"));
    metric.setAttribute("aria-label", `${title}: ${data.counts[key]}`); metrics.append(metric);
  }
  page.append(metrics);
  if (!data.counts.total) {
    const first = card("Začni sledovať svoje zariadenia", "Objavenie zariadenia ešte nezapína sledovanie. Skontroluj odporúčané zdroje a potvrď výber.");
    first.append(btn("Pridať zariadenia", () => app.go("discovery"), "primary")); page.append(first); return page;
  }
  const columns = el("div", null, "two-columns"), left = el("div"), right = el("div");
  left.append(list(app, "Čo potrebuje zásah", "Najdôležitejšie problémy sú navrchu. Detail ukáže príčinu, neistotu a ďalší krok.", data.urgent || [], "Momentálne nemáme doložený problém vyžadujúci zásah."));
  if ((data.alerts || []).some(alert => alert.device_count > 1)) {
    const groups = card("Spoločné výpadky");
    for (const alert of data.alerts.filter(alert => alert.device_count > 1)) groups.append(
      el("p", `${alert.device_count} zariadení · ${label(alert.cause)}`),
      btn("Preskúmať spoločný problém", () => app.go("incidents")));
    left.append(groups);
  }
  left.append(list(app, "Skontrolovať čoskoro", "Odporúčania vychádzajú z trendu, vlastných výmen a pozorovaných výpadkov.", data.prevention || [], "Zatiaľ nemáme podložené upozornenie na blížiaci sa problém."));
  right.append(list(app, "Kvalita sledovania", "Dostupný stav HA a dostatok histórie na predikciu sú samostatné informácie.", data.coverage || [], "Sledované zariadenia majú potrebné pokrytie."));
  const recent = card("Posledné zmeny");
  if (!(data.recent || []).length) recent.append(empty("História sa začne prvým vyhodnotením."));
  for (const change of data.recent || []) {
    const row = el("div", null, "device-line");
    row.append(btn(change.name || "Detail zariadenia", () => app.go("detail", { id: change.device_id }), "link"),
      el("span", `${label(change.state)} · ${ago(change.timestamp)}`, "muted")); recent.append(row);
  }
  right.append(recent); columns.append(left, right); page.append(columns);
  page.append(el("p", `Sledujeme ${data.counts.total} zariadení. Počty sú nad všetkými sledovanými záznamami; jednotlivé kategórie sa môžu prekrývať.`, "muted"));
  return page;
}
