import { UI_VERSION, btn, card, download, el, empty, field, select, table } from "./ui.js?v=0.2.0";

export function settingsView(app,data) {
  const page=el("div"), panel=card("Pravidlá integrácie","Predvolené pravidlá pre všetky zariadenia. Výnimky sa upravujú v detaile zariadenia."), key="global-settings", draft=app.draft(key,data.settings), form=el("div",null,"form");
  for(const [title,name,min,max] of [
    ["Nízka batéria (%)","low_battery_threshold",1,100],["Preventívny horizont (dni)","prevention_horizon_days",1,180],
    ["Tolerancia po štarte (min)","startup_grace_minutes",0,1440],["Stabilná obnova (min)","recovery_stability_minutes",0,60],
    ["Upozornenie pred výmenou (dni)","replacement_warning_days",1,90],["Uchovať históriu (dni)","retention_days",30,730],
    ["Opakovať neprečítané upozornenie (min, 0 = neopakovať)","notification_repeat_minutes",0,10080],
  ])form.append(field(title,"number",draft[name],value=>{draft[name]=Number(value);app.markDirty(key);},{min:String(min),max:String(max)}).wrapper);
  form.append(select("Natívne upozornenia HA",[["on","Zapnuté"],["off","Vypnuté"]],draft.notifications_enabled?"on":"off",value=>{draft.notifications_enabled=value==="on";app.markDirty(key);}));
  for(const [title,name] of [["Tiché hodiny od","quiet_start"],["Tiché hodiny do","quiet_end"]])form.append(field(title,"time",draft[name],value=>{draft[name]=value;app.markDirty(key);}).wrapper);
  panel.append(form,el("p","Tiché hodiny sa riadia časovou zónou HA. Explicitne kritické zariadenie môže upozorniť aj počas nich. Globálne vypnutie a odloženie platia vždy; zber dát a automatizačné udalosti pokračujú.","muted"),btn("Uložiť nastavenia",async()=>{
    await app.call("save_settings",{values:draft});app.clearDraft(key);await app.load(true);
  },"primary"));page.append(panel);
  const operations=card("Prevádzka a doplnkové nástroje"), facts=el("div",null,"facts");
  facts.append(el("p",`Rozhranie ${UI_VERSION} · backend ${data.meta?.backend_version || "neznámy"} · schéma ${data.meta?.schema_version || "—"}`),
    el("p",`Potvrdené migrácie: ${data.migration_count || 0}`));operations.append(facts);
  const actions=el("div",null,"actions");actions.append(
    btn("Batérie a zásoby",()=>app.go("stock")),
    btn("Jednorazový import Battery Notes",()=>app.go("migration")),
    btn("Katalóg modelov",()=>app.go("catalogue")),
    btn("Doplniť históriu pôvodných entít",async()=>{await app.call("load_native_history");app.showStatus("Dostupná história sa načítava na pozadí.");}),
    btn("Stiahnuť anonymizovanú diagnostiku",async()=>download("strazca-diagnostika.json",await app.call("get_diagnostics")))
  );operations.append(actions,el("p","Katalóg a zásoby pomáhajú údržbe. Sledovanie dostupnosti a batérie nevyžaduje katalógový záznam.","muted"));page.append(operations);return page;
}

export function stockView(app,data) {
  const page=card("Batérie a zásoby","Prehľad používaných typov a potvrdenej spotreby za posledných 90 dní. Neobsahuje nesledované zariadenia ani nabíjanie.");
  page.append(btn("Späť na nastavenia",()=>app.go("settings")));
  if(!data.items?.length)page.append(empty("Zatiaľ nemáme priradené batérie ani zásobu. Typ a počet doplníš v detaile zariadenia."));
  const rows=table(["Typ","V zariadeniach","Použité za 90 dní","Zásoba","Minimum","Odporúčaná rezerva","Správa"]);
  for(const item of data.items||[]) {
    const key=`stock:${item.battery_type}`, draft=app.draft(key,{on_hand:item.on_hand,minimum:item.minimum}), row=el("tr");
    row.append(el("td",item.battery_type),el("td",`${item.installed_quantity} ks / ${item.device_count} zariadení`),el("td",`${item.used_quantity} ks`));
    const onhand=el("td"), minimum=el("td");
    onhand.append(field(`Zásoba ${item.battery_type}`,"number",draft.on_hand,value=>{draft.on_hand=value===""?null:Number(value);app.markDirty(key);},{min:"0",max:"100000",placeholder:"Neevidovaná"}).wrapper);
    minimum.append(field(`Minimum ${item.battery_type}`,"number",draft.minimum,value=>{draft.minimum=Number(value);app.markDirty(key);},{min:"0",max:"100000"}).wrapper);
    const reserve=el("td");reserve.append(el("strong",`${item.suggested_reserve} ks`),el("p",item.basis==="confirmed_replacements"?"Vlastná potvrdená spotreba":"Používateľská minimálna rezerva","muted"));
    const action=el("td");action.append(btn(`Uložiť ${item.battery_type}`,async()=>{
      if(draft.on_hand===null||draft.on_hand===undefined) {app.showStatus("Najprv vyplň skutočnú zásobu.");return;}
      await app.call("save_stock",{battery_type:item.battery_type,on_hand:Number(draft.on_hand),minimum:Number(draft.minimum)});app.clearDraft(key);await app.load(true);
    }));
    row.append(onhand,minimum,reserve,action);rows.body.append(row);
  }
  page.append(rows.wrap);
  const add=el("div",null,"actions"), name=field("Nový typ batérie","text","",()=>{},{placeholder:"Napr. CR2032"}), qty=field("Nová zásoba","number",0,()=>{},{min:"0",max:"100000"});
  add.append(name.wrapper,qty.wrapper,btn("Pridať zásobu",async()=>{await app.call("save_stock",{battery_type:name.input.value,on_hand:Number(qty.input.value),minimum:0});await app.load(true);}));page.append(add);return page;
}

export function migrationView(app,data) {
  const page=card("Jednorazový import Battery Notes","Najprv skontroluj náhľad. Aplikovanie uchová samostatnú zálohu; Battery Notes odstraňuješ až po overení dát a reštarte.");
  page.append(btn("Späť na nastavenia",()=>app.go("settings")));
  if(!app.importPreview)page.append(btn("Pripraviť náhľad importu",async()=>{app.importPreview=await app.call("import_preview");app.paint();},"primary"));
  else {
    const p=app.importPreview;
    page.append(el("p",`Párované zariadenia: ${p.matched_device_count || 0} · nevyriešené: ${p.unmatched_count || 0} · výmenné cykly: ${p.cycle_count || 0} · vzorky: ${p.sample_count || 0}`));
    page.append(el("p",p.source_available?"Zdroj Battery Notes je dostupný.":"Zdroj Battery Notes sa nenašiel.","muted"));
    if(p.source_available)page.append(btn("Aplikovať skontrolovaný import",async()=>{
      if(!window.confirm("Aplikovať tento jednorazový import so zálohou?"))return;
      await app.call("import_apply",{receipt_id:p.receipt_id});app.importPreview=null;app.showStatus("Import bol aplikovaný. Over zariadenia a ich históriu.");await app.go("overview");
    },"primary"));
    page.append(btn("Nový náhľad",async()=>{app.importPreview=await app.call("import_preview");app.paint();}));
  }
  return page;
}

export function catalogueView(app,data) {
  const page=card("Katalóg modelov","Pomocná databáza na predvyplnenie typu batérie. Počet modelov nie je počet zariadení ani spotreba.");
  page.append(btn("Späť na nastavenia",()=>app.go("settings")),el("p",`Modelov: ${data.total}`,"muted"));
  const rows=table(["Výrobca","Model","Batéria","Zdroj"]);
  for(const item of data.items||[]) {const row=el("tr");[item.manufacturer||"—",item.model||"—",`${item.default_battery_type||"Neznámy typ"} × ${item.default_battery_quantity||1}`,item.source||"lokálny"].forEach(value=>row.append(el("td",value)));rows.body.append(row);}
  page.append(rows.wrap);
  if(data.has_more)page.append(btn("Ďalšie modely",async()=>{app.state.offset+=50;await app.load();}));
  if(app.state.offset)page.append(btn("Predchádzajúca strana",async()=>{app.state.offset=Math.max(0,app.state.offset-50);await app.load();}));
  return page;
}
