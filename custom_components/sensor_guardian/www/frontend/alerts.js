import { badge, btn, card, el, empty, label, select, time } from "./ui.js?v=0.2.0";

export function alertsView(app,data) {
  const page=el("div"), top=card("Upozornenia","Aktívne problémy a ich história. Potvrdenie prečítania nemení skutočnú dostupnosť.");
  top.append(select("Zobrazenie upozornení",[["active","Aktívne"],["all","Aj uzavreté"]],app.state.closed?"all":"active",async value=>{app.state.closed=value==="all";app.state.offset=0;await app.load();}));
  page.append(top);
  if(!data.items?.length)page.append(empty("Momentálne tu nie sú upozornenia pre tento výber."));
  for(const item of data.items || []) {
    const panel=card(item.device_count>1?`Spoločný problém · ${item.device_count} zariadení`:item.names?.[0]||"Upozornenie");
    panel.append(badge(item.closed_at?"Uzavreté":label(item.health_state),item.closed_at?"":"critical"),el("p",`Od ${time(item.opened_at)} · príčina: ${label(item.cause)} · istota: ${label(item.cause_confidence)}`,"muted"));
    if(item.cause==="unknown")panel.append(el("p","Príčina zostáva neznáma. Dostupné dôkazy nestačia na spoľahlivé rozlíšenie batérie a spojenia."));
    for(const point of item.evidence || [])panel.append(el("p",app.evidenceText(point),"muted"));
    const devices=el("div",null,"actions");
    (item.device_ids||[]).forEach((id,index)=>devices.append(btn(item.names?.[index]||"Detail zariadenia",()=>app.go("detail",{id}),"link")));panel.append(devices);
    if(!item.closed_at) {
      const actions=el("div",null,"actions");
      if(item.acknowledged)actions.append(badge("Prečítané"));
      else actions.append(btn("Potvrdiť prečítanie",async()=>{await app.call("acknowledge_alert",{incident_id:item.incident_id});await app.load();}));
      actions.append(btn("Odložiť na hodinu",async()=>{await app.call("acknowledge_alert",{incident_id:item.incident_id,minutes:60});await app.load();}));
      const cause=select("Potvrdiť príčinu",["unknown","battery","connectivity","gateway_upstream","integration","power_or_network"],item.cause||"unknown");
      actions.append(cause,btn("Potvrdiť príčinu",async()=>{await app.service("confirm_incident_cause",{incident_id:item.incident_id,cause:cause.value});await app.load();}));panel.append(actions);
      if(item.snoozed_until)panel.append(el("p",`Odložené do ${time(item.snoozed_until)}. Merania sa naďalej zbierajú.`,"muted"));
    }
    page.append(panel);
  }
  if(data.has_more)page.append(btn("Ďalšie upozornenia",async()=>{app.state.offset+=50;await app.load();}));
  if(app.state.offset)page.append(btn("Predchádzajúca strana",async()=>{app.state.offset=Math.max(0,app.state.offset-50);await app.load();}));
  return page;
}
