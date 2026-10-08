import { UI_VERSION, ago, btn, el, label } from "./frontend/ui.js?v=0.2.0";
import { styles } from "./frontend/styles.js?v=0.2.0";
import { dashboardView } from "./frontend/dashboard.js?v=0.2.0";
import { devicesView } from "./frontend/devices.js?v=0.2.0";
import { detailView } from "./frontend/detail.js?v=0.2.0";
import { alertsView } from "./frontend/alerts.js?v=0.2.0";
import { onboardingView } from "./frontend/onboarding.js?v=0.2.0";
import { catalogueView, migrationView, settingsView, stockView } from "./frontend/settings.js?v=0.2.0";

const views = { overview:dashboardView, devices:devicesView, detail:detailView,
  incidents:alertsView, discovery:onboardingView, settings:settingsView,
  stock:stockView, migration:migrationView, catalogue:catalogueView };
class SensorGuardianPanel extends HTMLElement {
  constructor() {
    super();this.attachShadow({mode:"open"});
    this.state={route:"overview",query:"",offset:0,days:30,filters:{filter:"all",sort:"risk"},closed:false,onboardingStep:"select"};
    this.selected=new Set();this.candidateChoices=new Map();this.drafts=new Map();this.dirtyKeys=new Set();
    this.loaded=false;this.sequence=0;this.pendingCount=null;this.status="";
    this.openDetails=new Set();
  }
  set hass(value) {
    this._hass=value;
    if(!this.loaded) {this.loaded=true;this.shell();this.load();}
  }
  get hass(){return this._hass;}
  connectedCallback(){clearInterval(this.timer);this.timer=setInterval(()=>this.autoRefresh(),30000);}
  disconnectedCallback(){clearInterval(this.timer);clearTimeout(this.searchTimer);this.sequence++;}
  shell(){
    const style=el("style");style.textContent=styles+" .mobile-list{display:none}@media(max-width:600px){.desktop-list{display:none}.mobile-list{display:block}}";
    const main=el("main"),header=el("header"),titles=el("div");
    titles.append(el("h1","Strážca senzorov"),el("p","Prevencia · dostupnosť · diagnostika","muted"));
    this.version=el("div",`Rozhranie ${UI_VERSION}`,"version");header.append(titles,this.version);
    const sticky=el("div",null,"sticky");this.nav=el("nav");this.nav.setAttribute("role","tablist");this.nav.setAttribute("aria-label","Sekcie Strážcu");
    for(const [route,title] of [["overview","Prehľad"],["devices","Zariadenia"],["incidents","Upozornenia"],["discovery","Pridať zariadenia"],["settings","Nastavenia"]]){
      const button=btn(title,()=>this.go(route));button.dataset.section=route;button.setAttribute("role","tab");button.setAttribute("aria-selected",String(route===this.state.route));
      this.nav.append(button);
    }
    const tools=el("div",null,"tools");this.search=el("input");this.search.type="search";this.search.placeholder="Hľadať zariadenie, oblasť alebo integráciu";this.search.setAttribute("aria-label","Hľadať");
    this.search.addEventListener("input",()=>{clearTimeout(this.searchTimer);this.searchTimer=setTimeout(async()=>{
      if(this.state.route==="detail")return;
      this.state.query=this.search.value;this.state.offset=0;
      if(this.state.route==="overview")await this.go("devices",{preserveQuery:true});else await this.load();
    },300);});
    tools.append(this.search,btn("Obnoviť",()=>this.load()));this.statusNode=el("div",null,"status");this.statusNode.setAttribute("role","status");this.statusNode.setAttribute("aria-live","polite");
    sticky.append(this.nav,tools,this.statusNode);this.banner=el("div");this.content=el("section");this.content.setAttribute("role","tabpanel");this.content.setAttribute("aria-label","Obsah Strážcu");
    main.append(header,sticky,this.banner,this.content);this.shadowRoot.replaceChildren(style,main);
    this.shadowRoot.addEventListener("guardian-error",event=>this.showError(event.detail));
  }
  draft(key,base){if(!this.drafts.has(key))this.drafts.set(key,structuredClone(base||{}));return this.drafts.get(key);}
  markDirty(key){this.dirtyKeys.add(key);this.updateStatus();}
  clearDraft(key){this.drafts.delete(key);this.dirtyKeys.delete(key);this.updateStatus();}
  showStatus(message){this.status=message;this.updateStatus();}
  showError(error){this.error=error?.message||String(error||"Údaje sa nepodarilo načítať.");this.updateStatus();}
  updateStatus(){
    if(!this.statusNode)return;
    this.statusNode.textContent=this.dirtyKeys.size?"Neuložené zmeny — automatické obnovenie formulára je pozastavené.":this.status;
    this.statusNode.classList.toggle("dirty",!!this.dirtyKeys.size);
    this.banner.replaceChildren();
    if(this.error)this.banner.append(el("div",this.error,"notice error"));
    else if(this.meta?.backend_version&&this.meta.backend_version!==UI_VERSION)this.banner.append(el("div",`Rozhranie ${UI_VERSION} a backend ${this.meta.backend_version} sa líšia. Dokonči aktualizáciu a reštart HA, potom obnov prehliadač.`,"notice error"));
    else if(this.meta?.evaluated_at&&Date.now()-new Date(this.meta.evaluated_at).getTime()>300000)this.banner.append(el("div","Posledné vyhodnotenie je staršie než päť minút. Zobrazené údaje môžu byť zastarané.","notice error"));
    this.version.textContent=`Rozhranie ${UI_VERSION} · backend ${this.meta?.backend_version||"čakáme"}`;
    if(this.meta?.evaluated_at&&!this.dirtyKeys.size&&!this.error)this.statusNode.textContent=[this.status,`Posledná kontrola ${ago(this.meta.evaluated_at)}`].filter(Boolean).join(" · ");
  }
  async call(name,values={}){
    try{return await this.hass.callWS({type:`sensor_guardian/${name}`,...values});}
    catch(error){this.showError(error.code==="unknown_command"?"HA ešte neposkytuje nové rozhranie. Over nainštalovanú verziu a reštart integrácie.":error);throw error;}
  }
  async service(name,values){try{return await this.hass.callService("sensor_guardian",name,values);}catch(error){this.showError(error);throw error;}}
  async go(route,options={}){
    if(this.dirtyKeys.size&&!window.confirm("Máš neuložené zmeny. Zahodiť ich a zmeniť sekciu?"))return;
    this.drafts.clear();this.dirtyKeys.clear();
    this.rememberDetails();
    if(options.state)this.state={...this.state,...options.state,filters:{...options.state.filters}};
    if(route==="detail")this.returnState={...this.state,filters:{...this.state.filters}};
    this.state.route=route;if(!options.state)this.state.offset=0;
    if(options.id)this.state.id=options.id;
    if(options.filter){this.state.filters.filter=options.filter;this.state.query="";this.search.value="";}
    if(!options.preserveQuery&&route!=="devices"){this.state.query="";this.search.value="";}
    this.error="";this.data=null;this.content.replaceChildren(el("p","Načítavam…","empty"));
    this.updateNav();await this.load(true);
    const heading=this.content.querySelector("h2");if(heading){heading.tabIndex=-1;heading.focus({preventScroll:true});}
  }
  async back(){const previous=this.returnState||{route:"devices",filters:{filter:"all",sort:"risk"},query:""};await this.go(previous.route,{state:previous,preserveQuery:true});this.search.value=this.state.query||"";}
  updateNav(){
    this.nav.querySelectorAll("[data-section]").forEach(button=>{
      const route=button.dataset.section;button.setAttribute("aria-selected",String(route===this.state.route||(this.state.route==="detail"&&route==="devices")||(["stock","migration","catalogue"].includes(this.state.route)&&route==="settings")));
      if(route==="discovery")button.textContent=`Pridať zariadenia${this.pendingCount===null?"":` (${this.pendingCount})`}`;
    });
  }
  async load(force=false){
    if(!this.hass||(!force&&this.dirtyKeys.size)){this.updateStatus();return;}
    const serial=++this.sequence,route=this.state.route;
    this.error="";this.status="Načítavam…";this.updateStatus();
    const paging={query:this.state.query,offset:this.state.offset,limit:50};
    try{
      let data;
      if(route==="overview")data=await this.call("get_dashboard");
      else if(route==="devices")data=await this.call("get_devices",{...paging,...this.state.filters});
      else if(route==="detail")data=await this.call("get_device_detail",{device_id:this.state.id,days:this.state.days});
      else if(route==="incidents")data=await this.call("get_alerts",{...paging,closed:this.state.closed});
      else if(route==="discovery")data=await this.call("get_candidates",paging);
      else if(route==="settings"||route==="migration")data=await this.call("get_settings");
      else if(route==="stock")data=await this.call("get_stock");
      else if(route==="catalogue")data=await this.call("get_data",{...paging,section:"batteries"});
      if(serial!==this.sequence||route!==this.state.route)return;
      if(route==="overview"&&typeof data?.counts?.total!=="number")throw new Error("Dashboard neposkytol platné súhrny.");
      for(const key of this.drafts.keys())if(!this.dirtyKeys.has(key))this.drafts.delete(key);
      this.data=data;this.meta=data.meta||this.meta;
      if(data.pending_count!==undefined)this.pendingCount=data.pending_count;
      if(route==="discovery")this.pendingCount=data.total;
      this.status=data.total!==undefined?`Záznamov: ${data.total}`:"Údaje načítané";this.paint();
    }catch(error){if(serial===this.sequence){this.showError(error);if(!this.data)this.content.replaceChildren(el("p","Údaje sa nepodarilo načítať. Skús Obnoviť a over aktívnu verziu integrácie.","empty"));}}
  }
  async autoRefresh(){
    if(!this.isConnected||this.dirtyKeys.size||["discovery","settings","stock","migration","catalogue"].includes(this.state.route))return;
    if(this.shadowRoot.activeElement?.matches("input,select,textarea"))return;
    await this.load();
  }
  paint(){
    if(!this.data)return;
    this.rememberDetails();
    const active=this.shadowRoot.activeElement,focusKey=active?.dataset.focusKey,focusLabel=active?.getAttribute("aria-label")||active?.textContent?.trim();
    this.updateNav();
    const render=views[this.state.route];this.content.replaceChildren(render(this,this.data));this.updateStatus();
    if(active&&this.shadowRoot.activeElement!==active){
      const matches=[...this.content.querySelectorAll("button,input,select")].filter(node=>focusKey?node.dataset.focusKey===focusKey:(node.getAttribute("aria-label")||node.textContent.trim())===focusLabel);
      if(matches.length===1)matches[0].focus({preventScroll:true});
    }
  }
  rememberDetails(){for(const item of this.content?.querySelectorAll("details[data-panel-id]")||[])item.open?this.openDetails.add(item.dataset.panelId):this.openDetails.delete(item.dataset.panelId);}
  evidenceText(point){
    const names={battery_level:"Posledná úroveň batérie",native_battery_low:"Natívne varovanie batérie",rssi_dbm:"RSSI",linkquality:"Kvalita spojenia",signal_trend:"Trend signálu",abnormal_drain:"Neobvyklý úbytok",source_entry_unavailable:"Zdrojová integrácia nedostupná",shared_outage_count:"Zariadenia v spoločnom výpadku"};
    const value=point.value===true?"áno":point.value===false?"nie":String(point.value??"neznáme");
    return `${names[point.feature]||"Pozorovaný dôkaz"}: ${point.feature==="signal_trend"&&value==="degrading"?"zhoršuje sa":value}${point.timestamp?` · ${ago(point.timestamp)}`:""}`;
  }
}
const PANEL_TAG=`sensor-guardian-panel-${UI_VERSION.replaceAll(".","-")}`;
if(!customElements.get(PANEL_TAG))customElements.define(PANEL_TAG,SensorGuardianPanel);
