import { card, el, empty, num, time } from "./ui.js?v=0.2.0";
const NS = "http://www.w3.org/2000/svg";
const svgNode = (tag, attrs = {}) => { const node = document.createElementNS(NS, tag); Object.entries(attrs).forEach(([key, value]) => node.setAttribute(key, String(value))); return node; };

export function chart(title, raw, unit = "", availability = [], cycles = []) {
  const panel = card(title);
  const points = raw.map(point => ({ ...point, timestamp: new Date(point.timestamp).getTime(), value: num(point.value) })).filter(point => Number.isFinite(point.timestamp)).sort((a,b) => a.timestamp - b.timestamp);
  const values = points.filter(point => point.value !== null);
  if (!values.length) { panel.append(empty("Zatiaľ nemáme použiteľnú históriu. Merania sa zbierajú počas sledovania.")); return panel; }
  const svg = svgNode("svg", { viewBox: "0 0 800 210", role: "img", "aria-label": title }); svg.classList.add("chart");
  const low = unit === "%" ? 0 : Math.min(...values.map(point => point.value)) - 3;
  const high = unit === "%" ? 100 : Math.max(...values.map(point => point.value)) + 3;
  const first = points[0].timestamp, last = points.at(-1).timestamp;
  const x = stamp => 55 + (stamp - first) / Math.max(1, last - first) * 715;
  const y = value => 170 - (value - low) / Math.max(1, high - low) * 140;
  for (let index = 0; index < 4; index++) {
    const value = low + (high - low) * index / 3;
    svg.append(svgNode("line", { x1:55, y1:y(value), x2:770, y2:y(value), stroke:"var(--divider-color,#dce3e9)" }));
    const text = svgNode("text", { x:46, y:y(value)+4, "text-anchor":"end", class:"chart-text" }); text.textContent = `${Math.round(value)}${unit}`; svg.append(text);
  }
  const outages = [];
  for (let index = 0; index < availability.length; index++) {
    if (availability[index].state !== "offline") continue;
    outages.push([new Date(availability[index].timestamp).getTime(), availability[index+1] ? new Date(availability[index+1].timestamp).getTime() : Date.now()]);
  }
  let path = "", previous = null;
  const boundaries = cycles.map(cycle => new Date(cycle.started_at).getTime()).filter(Number.isFinite);
  for (const stamp of boundaries.filter(stamp => stamp >= first && stamp <= last)) {
    svg.append(svgNode("line", { x1:x(stamp),x2:x(stamp),y1:25,y2:170,stroke:"var(--warning-color,#e6a23c)","stroke-dasharray":"4 4" }));
    const marker=svgNode("text", {x:x(stamp),y:18,class:"chart-text"});marker.textContent="Výmena";svg.append(marker);
  }
  for (const point of points) {
    if (point.value === null) { previous = null; continue; }
    const gap = previous && (point.timestamp - previous.timestamp > 3 * 86400000 || outages.some(([start,end]) => start < point.timestamp && end > previous.timestamp) || boundaries.some(stamp => stamp > previous.timestamp && stamp <= point.timestamp));
    path += `${!previous || gap ? "M" : "L"}${x(point.timestamp).toFixed(1)},${y(point.value).toFixed(1)} `; previous = point;
    svg.append(svgNode("circle", { cx:x(point.timestamp), cy:y(point.value), r:3, fill:"var(--primary-color,#008eab)" }));
  }
  svg.append(svgNode("path", { d:path, class:"series-line" }));
  for (const [stamp, align] of [[first,"start"], [last,"end"]]) {
    const text = svgNode("text", { x:x(stamp), y:195, "text-anchor":align, class:"chart-text" }); text.textContent = time(new Date(stamp).toISOString()); svg.append(text);
  }
  panel.append(svg, el("p", `${values.length} zobrazených bodov · skutočné pozorovania${points.some(point => point.resolution === "day") ? " a denné priemery" : ""}. Medzery a výpadky sa nevyplňujú.`, "muted small"));
  return panel;
}

export function availabilityHistory(points) {
  const panel = card("História dostupnosti");
  if (!points.length) { panel.append(empty("História prechodov sa začne prvým vyhodnotením zariadenia.")); return panel; }
  const names = { healthy:"Dostupné", offline:"Nedostupné", recovering:"Obnovuje sa", stale:"Bez hlásení", degraded:"Zhoršené", initializing:"Inicializácia", not_monitored:"Iba batéria", unknown:"Neznáme" };
  for (const point of points.slice(-20).reverse()) {
    const line = el("div", null, "device-line"); line.append(el("strong", names[point.state] || point.state), el("span", `${time(point.timestamp)}${point.provenance==="state_at_window_start"?" · posledný známy stav na začiatku obdobia":""}`, "muted")); panel.append(line);
  }
  return panel;
}
