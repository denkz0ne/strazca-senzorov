export const UI_VERSION = "0.2.0";
export const labels = {
  healthy: "Dostupné v HA", offline: "Nedostupné", stale: "Dlho bez údajov", degraded: "Zhoršený stav",
  recovering: "Obnovuje sa", initializing: "Inicializácia", unknown: "Neznáme", not_monitored: "Iba batéria",
  battery_and_availability: "Batéria aj dostupnosť", battery_only: "Iba batéria", availability_only: "Iba dostupnosť",
  replaceable_battery: "Vymeniteľná batéria", rechargeable: "Nabíjateľné", mains: "Sieťové napájanie",
  critical: "Vyžaduje zásah", attention: "Skontrolovať", watch: "Riziko", learning: "Učí sa", normal: "Bez varovania",
  paused: "Pozastavené", high: "Vysoká", medium: "Stredná", low: "Nízka", none: "Zatiaľ neurčená",
  battery_attention: "Pozornosť batérii",
  battery: "Batéria", connectivity: "Spojenie", gateway_upstream: "Spoločná brána / sieť",
  integration: "Zdrojová integrácia", power_or_network: "Napájanie alebo sieť", superseded: "Skupina sa zmenila",
};
export const reasons = {
  device_offline: "Hlavná entita je nedostupná.", availability_degraded: "Zariadenie hlási menej často než zvyčajne.",
  battery_low: "Nízka úroveň alebo natívne varovanie batérie.", rapid_drain: "Batéria ubúda neobvykle rýchlo.",
  replacement_window: "Odhadovaný interval výmeny sa blíži.", signal_degrading: "Dlhodobo sa zhoršuje signál.",
  availability_learning: "Interval hlásení sa ešte učí.", battery_source_missing: "Chýba použiteľný batériový údaj.", battery_observation_stale: "Batériový údaj je starší než 7 dní; over zdroj a spojenie.",
  estimate_learning: "Na odhad zatiaľ nestačí história.", signal_disabled: "Odporúčané signálové entity sú vypnuté.",
  insufficient_history: "Potrebujeme viac použiteľných meraní alebo vlastné výmenné cykly.",
  no_valid_samples: "Zatiaľ nemáme platné merania batérie.",
  recent_rapid_drain: "Výrazný pokles v posledných dňoch.", current_cycle_drain_trend: "Trend aktuálnej batérie.",
  same_device_cycle_history: "Odhad podľa výmen tohto zariadenia.", robust_median_pairwise_rate: "Odhad z odolného trendu meraní.",
  source_available_report_pattern_learning: "Zdroj HA je dostupný; periodicita sa učí.",
  source_entities_unavailable: "Hlavný zdroj HA je nedostupný.", native_availability_unavailable: "Zdroj výslovne hlási nedostupnosť.",
  battery_only_mode: "Dostupnosť sa v tomto režime nesleduje.", startup_grace: "Po štarte čakáme na obnovenie zdrojov.",
  report_pattern_not_periodic: "Bez spoľahlivej periodicity nemožno usúdiť výpadok iba z ticha.",
};
export const label = value => labels[value] || (value ? String(value) : "—");
export const reason = value => reasons[value] || "Podklady zatiaľ nestačia na podrobnejšie vysvetlenie.";
export function el(tag, text = null, className = "") {
  const node = document.createElement(tag); if (text !== null) node.textContent = String(text);
  if (className) node.className = className; return node;
}
export function btn(text, action, className = "") {
  const node = el("button", text, className); node.type = "button";
  node.addEventListener("click", async () => {
    if (node.disabled) return; node.disabled = true;
    try { await action(); } catch (error) { node.dispatchEvent(new CustomEvent("guardian-error", { detail: error, bubbles: true, composed: true })); }
    finally { node.disabled = false; }
  }); return node;
}
export function card(title, subtitle = "") {
  const node = el("section", null, "card"); node.append(el("h2", title));
  if (subtitle) node.append(el("p", subtitle, "muted")); return node;
}
export const empty = text => el("p", text, "empty");
export function num(value) {
  if (value === null || value === undefined || value === "" || typeof value === "boolean") return null;
  const number = Number(value); return Number.isFinite(number) ? number : null;
}
export const percent = value => num(value) === null ? "—" : `${num(value).toLocaleString("sk-SK", { maximumFractionDigits: 1 })} %`;
export function time(value) {
  if (!value) return "—"; const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "—" : date.toLocaleString("sk-SK", { dateStyle: "short", timeStyle: "short" });
}
export function ago(value) {
  if (!value) return "bez údajov"; const elapsed = (Date.now() - new Date(value).getTime()) / 60000;
  if (!Number.isFinite(elapsed)) return "bez údajov";
  if (elapsed < -1) return "čas je v budúcnosti";
  if (elapsed < 1) return "práve teraz";
  return elapsed < 60 ? `pred ${Math.floor(elapsed)} min` : elapsed < 1440 ? `pred ${Math.floor(elapsed / 60)} h` : `pred ${Math.floor(elapsed / 1440)} dňami`;
}
export const eta = estimate => estimate?.remaining_days_range ? `${estimate.remaining_days_range.min}–${estimate.remaining_days_range.max} dní` : "Odhad sa učí";
export const signal = device => (device.signal_values || []).map(item => `${String(item.kind).toUpperCase()} ${item.value}${item.kind === "rssi" ? " dBm" : ""}`).join(" · ") || ((device.recommended_signal_entities || []).length ? "Entity vypnuté" : "Bez merania");
export function badge(text, tone = "") { return el("span", text, `badge ${["critical","attention","watch","learning","normal","paused"].includes(tone) ? tone : ""}`); }
export function select(title, options, value = "", changed = () => {}) {
  const control = el("select"); control.setAttribute("aria-label", title);
  for (const option of options) {
    const [key, text] = Array.isArray(option) ? option : [option, label(option)];
    const node = el("option", text); node.value = key; control.append(node);
  }
  control.value = value; control.addEventListener("change", () => changed(control.value)); return control;
}
export function field(title, type, value, changed = () => {}, extra = {}) {
  const wrapper = el("label", null, "field"); wrapper.append(el("span", title));
  const input = el("input"); input.type = type; input.setAttribute("aria-label", title);
  input.value = value === null || value === undefined ? "" : String(value);
  Object.assign(input, extra); input.addEventListener("input", () => changed(input.value));
  wrapper.append(input); return { wrapper, input };
}
export function table(headers) {
  const wrap = el("div", null, "table-wrap"), node = el("table"), head = el("thead"), row = el("tr"), body = el("tbody");
  headers.forEach(title => row.append(el("th", title))); head.append(row); node.append(head, body); wrap.append(node);
  return { wrap, body };
}
export function kv(title, value) { const node = el("div", null, "kv"); node.append(el("span", title, "muted"), el("strong", value)); return node; }
export function download(name, value) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(value, null, 2)], { type: "application/json" }));
  const link = el("a"); link.href = url; link.download = name; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
}
