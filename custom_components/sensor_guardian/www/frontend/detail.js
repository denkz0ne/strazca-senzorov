import { ago, badge, btn, card, el, empty, eta, field, kv, label, percent, reason, select, signal, time } from "./ui.js?v=0.2.0";
import { availabilityHistory, chart } from "./charts.js?v=0.2.0";

function inputField(app, parent, key, name, type, base, property, extra = {}) {
  const draft = app.draft(key, base);
  const entry = field(name, type, draft[property], value => { draft[property] = value; app.markDirty(key); }, extra);
  parent.append(entry.wrapper); return entry.input;
}
export function detailView(app, data) {
  const device = data.device, page = el("div"), id = device.device_id;
  page.append(btn("Späť na zoznam", () => app.back()));
  const hero = el("div", null, "hero"), title = el("div");
  title.append(el("h2", device.name || "Sledované zariadenie"), el("p", [device.area_name, device.source_integration, label(device.power_type)].filter(Boolean).join(" · "), "muted"));
  hero.append(title, badge(label(device.health_state), device.health_state === "offline" ? "critical" : "")); page.append(hero);
  const overview = card("Stav a odporúčanie"), facts = el("div", null, "facts");
  facts.append(kv("Batéria", percent(device.battery_level)), kv("Odhad výdrže", device.power_type === "mains" ? "—" : eta(device.estimate)),
    kv("Signál", signal(device)), kv("Posledný zápis HA", ago(device.last_reported_at)));
  overview.append(facts, el("p", (device.risk?.reasons || []).map(reason).join(" ") || reason(device.health_reason)),
    el("p", "Dostupný stav HA nie je potvrdenie nového rádiového paketu.", "muted"));
  overview.append(el("p", `Batériový údaj: ${device.battery_observed_at ? time(device.battery_observed_at) : "zatiaľ bez nového pozorovania"}${device.battery_stale ? " · posledná známa hodnota, staršia než 7 dní" : ""}.`, "muted"));
  const actions = el("div", null, "actions");
  if (device.power_type === "replaceable_battery") actions.append(btn("Zaznamenať výmenu batérie", async () => {
    if (!window.confirm("Potvrdiť fyzickú výmenu batérie a začať nový cyklus?")) return;
    await app.service("mark_battery_replaced", { device_id:id, battery_type:device.battery_type || "", battery_quantity:device.battery_quantity || 1 }); await app.load(true);
  }));
  actions.append(btn("Odložiť upozornenia na hodinu", async () => { await app.service("snooze_device", { device_id:id, snooze_minutes:60 }); await app.load(true); }),
    btn("Obnoviť upozornenia", async () => { await app.service("resume_device", { device_id:id }); await app.load(true); }));
  if (device.recommended_signal_entities?.length) actions.append(btn("Zapnúť odporúčaný signál", async () => {
    if (!window.confirm("Zapnúť vypnuté signálové entity tohto zariadenia v HA?")) return;
    await app.call("enable_signal_entities", { device_id:id }); await app.load(true);
  }));
  overview.append(actions); page.append(overview);
  const periods = el("div", null, "actions");
  for (const days of [7,30,90]) periods.append(btn(`${days} dní`, async () => { app.state.days = days; await app.load(true); }, app.state.days === days ? "primary" : ""));
  page.append(periods);
  const graphs = el("div", null, "grid"), series = data.series || {};
  graphs.append(chart("Vývoj batérie", series.battery || [], "%", series.availability || [], data.cycles || []), availabilityHistory(series.availability || []));
  if ((series.voltage || []).length) graphs.append(chart("Napätie batérie", series.voltage, " V", series.availability || [], data.cycles || []));
  for (const kind of [...new Set((series.signal || []).map(row => row.kind))]) graphs.append(chart(`Vývoj signálu · ${String(kind).toUpperCase()}`, series.signal.filter(row => row.kind === kind), kind === "rssi" ? " dBm" : "", series.availability || []));
  if (!(series.signal || []).length) graphs.append(card("Signál sa ešte učí", device.recommended_signal_entities?.length ? "Odporúčané entity sú vypnuté. Po ich potvrdenom zapnutí začneme ukladať históriu." : "Zdroj zatiaľ neposkytol použiteľné signálové údaje."));
  page.append(graphs);
  const replacements = card("História výmen batérie");
  for (const cycle of (data.cycles || []).slice(-10).reverse()) replacements.append(el("p", `${time(cycle.started_at)} · ${cycle.battery_type || "typ neevidovaný"} × ${cycle.battery_quantity || 1} · ${cycle.provenance === "user_confirmed" ? "potvrdená fyzická výmena" : "importovaný záznam"}`));
  if (!(data.cycles || []).length) replacements.append(empty("Zatiaľ nie je zaznamenaná fyzická výmena. Nabíjanie nie je výmena batérie."));
  page.append(replacements);
  const analysis = el("div", null, "grid"), prediction = card("Podklady predikcie"), diagnosis = card("Diagnostika príčiny");
  prediction.append(kv("Interval výdrže", eta(device.estimate)), kv("Istota odhadu", label(device.estimate?.confidence)),
    el("p", `${device.sample_count || 0} batériových vzoriek · ${device.span_days || 0} dní pokrytia · ${device.report_count || 0} hlásení vybraného zdroja.`, "muted"));
  const why = el("ul", null, "reason-list"); (device.estimate?.reason_codes || ["no_valid_samples"]).forEach(code => why.append(el("li", reason(code)))); prediction.append(why);
  diagnosis.append(kv("Príčina", label(device.cause)), el("p", device.cause === "unknown" ? "Dôkazy zatiaľ nestačia alebo si odporujú. Neznáma príčina nie je potvrdenie vybitej batérie." : "Ide o odhad z pozorovaných dôkazov; môže sa spresniť ďalšími údajmi.", "muted"));
  for (const incident of (data.incidents || []).slice(0,3)) {
    diagnosis.append(el("p", `${time(incident.opened_at)} · ${label(incident.cause)} · ${incident.closed_at ? "uzavreté" : "aktívne"}`));
    for (const point of incident.evidence || []) diagnosis.append(el("p", app.evidenceText(point), "muted"));
    if (!incident.closed_at && incident.kind !== "battery") {
      const choice = select("Potvrdiť príčinu", ["unknown","battery","connectivity","gateway_upstream","integration","power_or_network"], incident.cause || "unknown");
      diagnosis.append(choice, btn("Potvrdiť príčinu", async () => { await app.service("confirm_incident_cause", { incident_id:incident.incident_id, cause:choice.value }); await app.load(true); }));
    }
  }
  if (!(data.incidents || []).length) diagnosis.append(empty("Pri zariadení zatiaľ neevidujeme incident."));
  analysis.append(prediction,diagnosis); page.append(analysis);

  const tracking = card("Sledovanie zariadenia"), trackKey = `tracking:${id}`;
  const track = app.draft(trackKey, { tracking_mode:device.tracking_mode === "ignored" ? "availability_only" : device.tracking_mode, power_type:device.power_type });
  const trackForm = el("div", null, "form");
  for (const [name,key,options] of [["Režim sledovania","tracking_mode",["battery_and_availability","availability_only","battery_only"]], ["Napájanie","power_type",["replaceable_battery","rechargeable","mains","unknown"]]]) trackForm.append(select(name, options, track[key], value => { track[key]=value; app.markDirty(trackKey); }));
  tracking.append(trackForm, btn("Uložiť sledovanie", async () => { await app.call("update_tracking", { device_id:id, ...track }); app.clearDraft(trackKey); await app.load(true); }),
    btn(device.tracking_mode === "ignored" ? "Obnoviť sledovanie" : "Pozastaviť sledovanie", async () => {
      if (device.tracking_mode !== "ignored" && !window.confirm("Pozastaviť sledovanie? História zostane uložená.")) return;
      await app.call("set_tracking_active", { device_id:id, active:device.tracking_mode === "ignored" }); await app.load(true);
    }));
  page.append(tracking);
  const rules = card("Pravidlá zariadenia", "Prázdne hodnoty sa dedia z nastavení integrácie. Zmeň iba výnimky, ktoré potrebuješ."), rulesKey = `rules:${id}`, rulesForm = el("div", null, "form"), base = device.rules || {};
  for (const [name,key,min,max] of [["Nízka batéria (%)","low_battery_threshold",1,100],["Preventívny horizont (dni)","prevention_horizon_days",1,180],["Tolerancia po štarte (min)","startup_grace_minutes",0,1440],["Stabilná obnova (min)","recovery_stability_minutes",0,60]]) inputField(app,rulesForm,rulesKey,name,"number",base,key,{ min:String(min),max:String(max),placeholder:String(data.inherited_rules?.[key] ?? "Zdediť") });
  const ruleDraft = app.draft(rulesKey,base);
  rulesForm.append(select("Kritickosť zariadenia", [["inherit","Bežné / zdedené"],["normal","Bežné"],["critical","Kritické — môže upozorniť v tichých hodinách"]], ruleDraft.criticality || "inherit", value => { value === "inherit" ? delete ruleDraft.criticality : ruleDraft.criticality=value; app.markDirty(rulesKey); }));
  rules.append(rulesForm,btn("Uložiť pravidlá",async () => {
    const values = {}; for (const [key,value] of Object.entries(ruleDraft)) if (value !== "" && value !== null && value !== undefined) values[key] = ["criticality"].includes(key) || typeof value === "boolean" ? value : Number(value);
    await app.call("update_device_rules",{ device_id:id,values }); app.clearDraft(rulesKey); await app.load(true);
  })); page.append(rules);
  if (device.power_type !== "mains" && ["battery_only","battery_and_availability"].includes(device.tracking_mode)) {
    const battery = card("Informácie o batérii", "Typ a počet slúžia evidencii výmen a zásob. Sledovanie údajov funguje aj bez katalógového modelu."), key=`battery:${id}`, form=el("div",null,"form"), baseBattery={ battery_type:device.battery_type || "",battery_quantity:device.battery_quantity || 1 };
    inputField(app,form,key,"Typ batérie","text",baseBattery,"battery_type",{ placeholder:"Napr. CR2450" });
    inputField(app,form,key,"Počet batérií","number",baseBattery,"battery_quantity",{ min:"1",max:"20" });
    battery.append(form, btn("Uložiť batériu",async()=>{ const value=app.draft(key,baseBattery); await app.call("update_battery",{device_id:id,battery_type:value.battery_type,battery_quantity:Number(value.battery_quantity),power_type:device.power_type==="unknown"?"unknown":device.power_type}); app.clearDraft(key); await app.load(true); })); page.append(battery);
  }
  const sources=card("Zdroje a kvalita údajov"), advanced=el("details"), summary=el("summary","Pokročilá diagnostika zdrojov"); advanced.dataset.panelId=`sources:${id}`;advanced.open=app.openDetails?.has(advanced.dataset.panelId);advanced.append(summary);
  for (const [kind,entity] of Object.entries(data.sources?.entity_refs || {})) if(entity) advanced.append(el("p", `${kind}: ${entity}`, "source-id"));
  const sourceKey=`sources:${id}`, sourceDraft=app.draft(sourceKey,{entity_refs:{...data.sources?.entity_refs},availability_entity:data.sources?.availability_entity||null}), sourceForm=el("div",null,"form");
  for(const [name,kind] of [["Percento batérie","battery_level"],["Natívne slabá batéria","battery_low"],["Napätie batérie","voltage"],["Natívne pripojenie","native_availability"]]){
    const choices=(data.source_choices||[]).filter(row=>row.kind===kind&&!row.disabled).map(row=>[row.entity_id,row.name]);
    sourceForm.append(select(name,[["","Nepoužiť"],...choices],sourceDraft.entity_refs[kind]||"",value=>{sourceDraft.entity_refs[kind]=value||null;app.markDirty(sourceKey);}));
  }
  sourceForm.append(select("Primárna entita dostupnosti",[["","Natívne pripojenie"],...(data.source_choices||[]).filter(row=>!row.disabled).map(row=>[row.entity_id,row.name])],sourceDraft.availability_entity||"",value=>{sourceDraft.availability_entity=value||null;app.markDirty(sourceKey);}));
  advanced.append(el("p","Mení sa iba to, ktoré pôvodné entity Strážca sleduje. Žiadna entita sa nepremenuje. Neznáma periodicita nie je dôkaz výpadku.","muted"),sourceForm,
    btn("Uložiť výber zdrojov",async()=>{await app.call("update_sources",{device_id:id,...sourceDraft});app.clearDraft(sourceKey);await app.load(true);}),
    btn("Použiť automatické zdroje",async()=>{await app.call("update_sources",{device_id:id,automatic:true});app.clearDraft(sourceKey);await app.load(true);}),
    btn("Začať učenie intervalu nanovo",async()=>{if(!window.confirm("Obnoviť iba naučený interval? Merania a výmeny zostanú."))return;await app.call("reset_report_profile",{device_id:id});await app.load(true);}));
  sources.append(el("p",(device.quality?.missing || []).map(reason).join(" ") || "Zdroje poskytujú potrebné údaje.","muted"),advanced,
    btn("Doplniť dostupnú históriu HA",async()=>{ await app.call("load_native_history"); app.showStatus("História sa načítava na pozadí. Chýbajúce alebo vymazané dáta sa nedopĺňajú odhadom."); }));
  page.append(sources); return page;
}
