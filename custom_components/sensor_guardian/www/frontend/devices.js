import { ago, badge, btn, card, el, empty, eta, label, percent, reason, select, signal, table } from "./ui.js?v=0.2.0";

export function devicesView(app, data) {
  const page = card("Sledované zariadenia", "Zariadenia, ktorých stav Strážca vyhodnocuje. Nové kandidáty nájdeš v Pridať zariadenia.");
  const filters = el("div", null, "filters");
  const values = app.state.filters;
  for (const [title, key, options] of [
    ["Zobraziť", "filter", [["all","Všetky"],["offline","Nedostupné"],["attention","Potrebujú zásah"],["prevention","Rizikové"],["coverage","Chýbajúce údaje"],["battery","Batériové"],["paused","Pozastavené"]]],
    ["Oblasť", "area", [["","Všetky oblasti"], ...(data.filters?.areas || []).map(name => [name,name])]],
    ["Integrácia", "integration", [["","Všetky integrácie"], ...(data.filters?.integrations || []).map(name => [name,name])]],
    ["Napájanie", "power", [["","Všetky napájania"],"replaceable_battery","rechargeable","mains","unknown"]],
    ["Triedenie", "sort", [["risk","Priorita zásahu"],["name","Názov"],["battery","Úroveň batérie"]]],
  ]) filters.append(select(title, options, values[key] || (key === "sort" ? "risk" : key === "filter" ? "all" : ""), async value => { values[key] = value; app.state.offset = 0; await app.load(); }));
  filters.append(btn("Zrušiť filtre", async () => { app.state.filters = { filter:"all", sort:"risk" }; app.state.query = ""; app.search.value = ""; app.state.offset = 0; await app.load(); }));
  page.append(filters, el("p", `Záznamov: ${data.total}`, "count"));
  if (!data.items?.length) { page.append(empty("Pre tento výber zatiaľ nie sú zariadenia.")); return page; }
  const desktop = table(["Zariadenie", "Dostupnosť", "Prevencia", "Batéria", "Výdrž", "Signál", "Posledný údaj"]);
  desktop.wrap.classList.add("desktop-list");
  const mobile = el("div", null, "mobile-list");
  for (const device of data.items) {
    const row = el("tr"), name = el("td");
    name.append(btn(device.name || "Sledované zariadenie", () => app.go("detail", { id:device.device_id }), "link"),
      el("p", [device.identifier, device.area_name, device.source_integration].filter(Boolean).join(" · "), "muted"));
    const availability = el("td"), risk = el("td");
    availability.append(badge(label(device.health_state), device.health_state === "offline" ? "critical" : ""));
    risk.append(badge(label(device.risk?.level), device.risk?.level));
    row.append(name, availability, risk, el("td", percent(device.battery_level)), el("td", device.power_type === "mains" ? "—" : eta(device.estimate)), el("td", signal(device)), el("td", ago(device.last_reported_at)));
    desktop.body.append(row);
    const item = el("div", null, "device-line"), info = el("div", null, "device-info"), status = el("div");
    info.append(btn(device.name || "Sledované zariadenie", () => app.go("detail", { id:device.device_id }), "link"),
      el("p", [device.area_name, device.source_integration].filter(Boolean).join(" · "), "muted"),
      el("p", (device.risk?.reasons || []).map(reason).join(" ") || label(device.health_state), "small"));
    status.append(badge(label(device.health_state), device.health_state === "offline" ? "critical" : ""),
      el("p", percent(device.battery_level), "muted")); item.append(info,status); mobile.append(item);
  }
  page.append(desktop.wrap, mobile);
  if (data.has_more) page.append(btn("Ďalšia strana", async () => { app.state.offset += 50; await app.load(); }, "pagination"));
  if (app.state.offset) page.append(btn("Predchádzajúca strana", async () => { app.state.offset = Math.max(0, app.state.offset - 50); await app.load(); }, "pagination"));
  return page;
}
