import { badge, btn, card, el, empty, field, label, percent, select, table } from "./ui.js?v=0.2.0";

export function onboardingView(app, data) {
  const page = el("div"), steps = el("div", null, "step");
  const current = app.state.onboardingStep || "select";
  for (const [key,text] of [["select","1 · Výber"],["review","2 · Kontrola"],["result","3 · Výsledok"]]) steps.append(el("span",text,current===key?"current":""));
  page.append(steps);
  if (current === "result") {
    const result = app.onboardingResult, summary = card(result.applied ? "Sledovanie bolo zapnuté" : "Sledovanie sa nezačalo",
      result.applied ? "Zariadenia začali poskytovať údaje Strážcovi. Pomocné HA entity sa môžu ešte inicializovať." : "Zdroje alebo dostupnosť kandidátov sa zmenili. Žiadny blokovaný riadok sa nepovažuje za úspešný.");
    for (const row of result.results || []) summary.append(el("p", `${row.name || "Zariadenie"} · ${row.status==="tracked"?"Sleduje sa":row.status==="source_changed"?"Zdroj sa zmenil":"Pridanie je blokované"}`));
    summary.append(btn(result.applied ? "Späť na kandidátov" : "Znovu skontrolovať", async()=> {
      if (!result.applied) await review(app); else { app.state.onboardingStep="select"; app.selected.clear(); app.candidateChoices.clear(); await app.load(true); }
    }, "primary")); page.append(summary); return page;
  }
  if (current === "review") {
    const panel = card("Skontroluj zapnutie sledovania", "Tento náhľad ešte nič nepridal. Po potvrdení sa zdroje skontrolujú znova.");
    for (const item of app.preview.items) {
      const row = el("div",null,"device-line"), info=el("div");
      info.append(el("strong",item.name), el("p",`${label(item.tracking_mode)} · ${label(item.power_type)} · ${item.source_integration}`,"muted"));
      if(item.battery_type) info.append(el("p",`Batéria: ${item.battery_type} × ${item.battery_quantity || 1}`,"muted"));
      if(item.enable_signals) info.append(el("p",`Po potvrdení zapneme ${item.recommended_signal_entities?.length || 0} odporúčaných signálových entít.`,"muted"));
      else if(item.recommended_signal_entities?.length) info.append(el("p","Signálové entity zostanú vypnuté; možno ich zapnúť neskôr v detaile.","muted"));
      row.append(info,badge("Pripravené")); panel.append(row);
    }
    const actions=el("div",null,"actions");
    actions.append(btn("Začať sledovať",async()=>{
      const result=await app.call("apply_tracking",{preview_id:app.preview.preview_id});
      app.onboardingResult=result; app.state.onboardingStep="result"; app.dirtyKeys.clear(); app.paint();
    },"primary"),btn("Upraviť výber",()=>{app.state.onboardingStep="select";app.paint();}));
    panel.append(actions); page.append(panel); return page;
  }
  const panel = card("Pridať zariadenia", "Vyber nové zariadenia. Režim a napájanie sa odporúčajú osobitne pre každý riadok; typ batérie možno doplniť neskôr.");
  const actions=el("div",null,"actions"), selection=el("span", `Vybrané: ${app.selected.size}`, "muted");
  const checkAll=el("input"); checkAll.type="checkbox"; checkAll.setAttribute("aria-label","Vybrať zobrazené zariadenia");
  checkAll.checked=!!data.items?.length && data.items.every(item=>app.selected.has(item.device_id));
  checkAll.addEventListener("change",()=>{for(const item of data.items || []) checkAll.checked?app.selected.add(item.device_id):app.selected.delete(item.device_id);app.paint();});
  actions.append(checkAll,selection,btn("Skontrolovať výber",()=>review(app),"primary")); panel.append(actions);
  if(!data.items?.length) {panel.append(empty("Nie sú tu nevyriešené kandidáty. Už sledované a ignorované zariadenia sa neponúkajú."));page.append(panel);return page;}
  const rows=table(["Vybrať","Zariadenie","Údaje","Sledovanie a napájanie","Voliteľné informácie"]);
  for(const item of data.items) {
    const choice=app.candidateChoices.get(item.device_id)||{
      device_id:item.device_id, tracking_mode:item.suggested_mode, power_type:item.power_type||"unknown",
      battery_type:item.battery_type||"", battery_quantity:item.battery_quantity||1, enable_signals:false,
    }; app.candidateChoices.set(item.device_id,choice);
    const row=el("tr"), checkCell=el("td"), check=el("input");check.type="checkbox";check.checked=app.selected.has(item.device_id);check.setAttribute("aria-label",`Vybrať ${item.name}`);
    check.addEventListener("change",()=>{check.checked?app.selected.add(item.device_id):app.selected.delete(item.device_id);selection.textContent=`Vybrané: ${app.selected.size}`;});
    checkCell.append(check);
    const name=el("td");name.append(el("strong",item.name),el("p",[item.area_name,item.source_integration,item.manufacturer,item.model].filter(Boolean).join(" · "),"muted"));
    const available=el("td"), source=item.entity_refs?.battery_level, state=source&&app.hass.states?.[source];
    available.append(el("p",item.has_battery_data?`Batéria: ${percent(state?.state)}`:"Sledovanie dostupnosti"),
      el("p",item.recommended_signal_entities?.length?"Odporúčaný signál je vypnutý.":"Použiteľné natívne zdroje.","muted"));
    const config=el("td");
    config.append(select(`Režim ${item.name}`,item.has_battery_data?["battery_and_availability","availability_only","battery_only"]:["availability_only"],choice.tracking_mode,value=>{choice.tracking_mode=value;}),
      select(`Napájanie ${item.name}`,["replaceable_battery","rechargeable","mains","unknown"],choice.power_type,value=>{choice.power_type=value;}));
    const optional=el("td"), type=field(`Typ batérie ${item.name}`,"text",choice.battery_type,value=>{choice.battery_type=value;},{placeholder:"Voliteľné"}), quantity=field(`Počet ${item.name}`,"number",choice.battery_quantity,value=>{choice.battery_quantity=Number(value);},{min:"1",max:"20"});
    if(item.has_battery_data) optional.append(type.wrapper,quantity.wrapper);
    if(item.recommended_signal_entities?.length) {
      const enable=el("label",null,"check"), checkbox=el("input");checkbox.type="checkbox";checkbox.checked=choice.enable_signals;checkbox.setAttribute("aria-label",`Zapnúť odporúčaný signál ${item.name}`);checkbox.addEventListener("change",()=>{choice.enable_signals=checkbox.checked;});
      enable.append(checkbox,el("span","Po potvrdení zapnúť odporúčaný signál"));optional.append(enable);
    }
    optional.append(btn("Ignorovať",async()=>{if(!window.confirm(`Ignorovať ${item.name}? Nebude sa sledovať.`))return;await app.call("dismiss_candidate",{device_id:item.device_id});app.selected.delete(item.device_id);await app.load(true);}));
    row.append(checkCell,name,available,config,optional);rows.body.append(row);
  }
  panel.append(rows.wrap,el("p",`Čakajúcich kandidátov: ${data.total}. Výber môže pokračovať na ďalšej stránke; najviac 100 na jeden náhľad.`,"muted"));
  if(data.has_more) panel.append(btn("Ďalšia strana kandidátov",async()=>{app.state.offset+=50;await app.load(true);}));
  if(app.state.offset)panel.append(btn("Predchádzajúca strana",async()=>{app.state.offset=Math.max(0,app.state.offset-50);await app.load(true);}));
  page.append(panel);return page;
}
async function review(app) {
  if(!app.selected.size) {app.showStatus("Najprv vyber aspoň jedno zariadenie.");return;}
  app.preview=await app.call("preview_tracking",{device_ids:[...app.selected],choices:[...app.selected].map(id=>app.candidateChoices.get(id)).filter(Boolean)});
  app.state.onboardingStep="review";app.paint();
}
