/* Self-hosted, dependency-free Home Assistant management panel. */
class SensorGuardianPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this.section = "overview";
    this.offset = 0;
    this.limit = 30;
    this.query = "";
    this.items = [];
    this.page = null;
    this.status = "";
    this.preview = null;
    this.loaded = false;
  }

  set hass(value) {
    this._hass = value;
    if (!this.loaded) {
      this.loaded = true;
      this.render();
      this.refresh();
    }
  }

  get hass() {
    return this._hass;
  }

  render() {
    this.shadowRoot.innerHTML = `
      <style>
        :host { display:block; color:var(--primary-text-color); background:var(--primary-background-color); min-height:100%; }
        main { max-width:1180px; margin:auto; padding:24px; box-sizing:border-box; }
        h1 { font-size:24px; margin:0 0 18px; }
        nav { display:flex; flex-wrap:wrap; gap:8px; margin-bottom:16px; border-bottom:1px solid var(--divider-color); padding-bottom:12px; }
        button, input, select { font:inherit; color:inherit; background:var(--card-background-color); border:1px solid var(--divider-color); border-radius:8px; padding:9px 12px; }
        button { cursor:pointer; }
        button[aria-selected="true"] { background:var(--primary-color); color:var(--text-primary-color,#fff); }
        button:focus-visible, input:focus-visible, select:focus-visible { outline:2px solid var(--primary-color); outline-offset:2px; }
        .tools { display:flex; gap:8px; margin:0 0 14px; }
        .tools input { flex:1; min-width:80px; }
        #status { min-height:24px; color:var(--secondary-text-color); }
        .card { background:var(--card-background-color); border-radius:12px; padding:16px; margin:10px 0; box-shadow:var(--ha-card-box-shadow,0 1px 3px #0002); }
        .title { font-size:17px; font-weight:600; margin-bottom:8px; }
        .meta { color:var(--secondary-text-color); line-height:1.5; overflow-wrap:anywhere; }
        .actions { display:flex; flex-wrap:wrap; gap:8px; margin-top:12px; align-items:center; }
        .empty { padding:28px 12px; text-align:center; color:var(--secondary-text-color); }
        .badge { display:inline-block; border-radius:999px; padding:3px 9px; background:var(--secondary-background-color); margin-right:6px; }
        .problem { color:var(--error-color); }
        @media(max-width:600px) { main { padding:14px; } nav { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); } nav button { width:100%; } .tools { flex-direction:column; } }
      </style>
      <main>
        <h1>Strážca senzorov</h1>
        <nav role="tablist" aria-label="Sekcie Strážcu senzorov">
          <button role="tab" data-section="overview" aria-selected="true">Prehľad</button>
          <button role="tab" data-section="batteries" aria-selected="false">Batérie</button>
          <button role="tab" data-section="devices" aria-selected="false">Zariadenia</button>
          <button role="tab" data-section="incidents" aria-selected="false">Incidenty</button>
          <button role="tab" data-section="settings" aria-selected="false">Nastavenia</button>
        </nav>
        <div class="tools"><input id="search" type="search" aria-label="Hľadať v sekcii" placeholder="Hľadať"><button id="reload">Obnoviť</button></div>
        <div id="status" role="status" aria-live="polite"></div>
        <section id="content" role="tabpanel" aria-label="Obsah sekcie"></section>
        <button id="more" hidden>Načítať ďalšie</button>
      </main>`;
    this.shadowRoot.querySelectorAll("[data-section]").forEach((button) => {
      button.addEventListener("click", () => {
        this.section = button.dataset.section;
        this.shadowRoot.querySelectorAll("[data-section]").forEach((tab) => {
          tab.setAttribute("aria-selected", String(tab === button));
        });
        this.offset = 0;
        this.refresh();
      });
    });
    this.shadowRoot.getElementById("reload").addEventListener("click", () => this.refresh());
    this.shadowRoot.getElementById("more").addEventListener("click", () => {
      this.offset += this.limit;
      this.refresh(true);
    });
    let timer;
    this.shadowRoot.getElementById("search").addEventListener("input", (event) => {
      clearTimeout(timer);
      timer = setTimeout(() => {
        this.query = event.target.value;
        this.offset = 0;
        this.refresh();
      }, 250);
    });
  }

  async refresh(append = false) {
    if (!this.hass) return;
    this.status = "Načítavam…";
    this.paintStatus();
    try {
      this.page = await this.hass.callWS({
        type: "sensor_guardian/get_data",
        section: this.section === "devices" ? "discovery" : this.section,
        offset: this.offset,
        limit: this.limit,
        query: this.query,
      });
      if (!append) this.items = [];
      this.items = [...this.items, ...(this.page.items || [])];
      this.status = this.page.total === undefined ? "" : `Záznamov: ${this.page.total}`;
      this.paint();
    } catch (error) {
      this.status = error.message || "Údaje sa nepodarilo načítať.";
      this.paintStatus();
      this.shadowRoot.getElementById("content").replaceChildren();
    }
  }

  paintStatus() {
    this.shadowRoot.getElementById("status").textContent = this.status;
  }

  paint() {
    const content = this.shadowRoot.getElementById("content");
    content.replaceChildren();
    if (this.section === "settings") this.renderSettings(content);
    else if (this.section === "devices") this.renderCandidates(content);
    else if (this.section === "batteries") this.renderBatteries(content);
    else this.renderRecords(content, this.items);
    const more = this.shadowRoot.getElementById("more");
    more.hidden = !this.page?.has_more;
    this.paintStatus();
  }

  renderRecords(content, records) {
    if (!records.length) return this.empty(content, "Zatiaľ tu nie sú žiadne záznamy.");
    records.forEach((item) => {
      const card = this.card(content, item.name || item.model || item.incident_id || item.device_id || "Záznam");
      const status = item.health_state || item.status;
      if (status) this.badge(card, this.label(status), status === "offline" || status === "stale");
      if (item.cause) this.badge(card, `Príčina: ${this.label(item.cause)}`);
      const detail = [];
      if (item.last_reported_at) detail.push(`Posledné hlásenie: ${item.last_reported_at}`);
      if (item.battery_attention !== undefined) detail.push(`Batéria: ${item.battery_attention ? "vyžaduje pozornosť" : "bez upozornenia"}`);
      if (item.device_ids) detail.push(`Zariadenia: ${item.device_ids.length}`);
      if (item.cause_confidence) detail.push(`Istota: ${this.label(item.cause_confidence)}`);
      this.text(card, detail.join(" · ") || "Podrobnosti nie sú k dispozícii.", "meta");
      if (item.device_id) this.deviceActions(card, item);
      if (item.incident_id && !item.closed_at) this.confirmCause(card, item.incident_id);
    });
    if (!records.length) this.empty(content, "Žiadne výsledky pre toto hľadanie.");
  }

  renderCandidates(content) {
    if (!this.items.length) return this.empty(content, "Nenašli sa nové odporúčania zariadení.");
    this.items.forEach((item) => {
      const card = this.card(content, item.device_id);
      this.text(card, `${this.label(item.suggested_mode)} · zhoda ${this.label(item.confidence)}`, "meta");
      this.text(card, (item.reasons || []).join("; ") || "Dôvod odporúčania nie je dostupný.", "meta");
      if ((item.recommended_signal_entities || []).length) {
        this.text(card, `Vypnuté signálové entity, ktoré môžu zlepšiť diagnostiku: ${item.recommended_signal_entities.join(", ")}. Strážca ich sám nezapína.`, "meta");
      }
      const actions = this.actions(card);
      const mode = this.select(actions, "Režim sledovania", [item.suggested_mode, "availability_only", "battery_only", "battery_and_availability"]);
      const power = this.select(actions, "Napájanie", ["replaceable_battery", "rechargeable", "mains", "unknown"]);
      this.button(actions, "Sledovať", async () => {
        await this.command({ type: "sensor_guardian/track_device", device_id: item.device_id, tracking_mode: mode.value, power_type: power.value });
        await this.refresh();
      });
      this.button(actions, "Ignorovať", async () => {
        await this.command({ type: "sensor_guardian/dismiss_candidate", device_id: item.device_id });
        await this.refresh();
      });
    });
  }

  renderBatteries(content) {
    const cycles = this.page?.related?.cycles || [];
    const trackedDevices = this.page?.related?.tracked_devices || [];
    if (!this.items.length && !cycles.length && !trackedDevices.length) return this.empty(content, "Katalóg alebo história sa zatiaľ nenačítali.");
    const addCard = this.card(content, "Pridať model batérie");
    const addActions = this.actions(addCard);
    const manufacturer = this.textInput(addActions, "Výrobca");
    const modelName = this.textInput(addActions, "Model zariadenia");
    const batteryType = this.textInput(addActions, "Typ batérie (napr. CR2032)");
    const quantity = this.numberInput(addActions, "Počet batérií", 1, 20, 1);
    const power = this.select(addActions, "Napájanie batérie", ["replaceable_battery", "rechargeable", "unknown"]);
    this.button(addActions, "Pridať do katalógu", async () => {
      await this.command({ type: "sensor_guardian/add_model", manufacturer: manufacturer.value, model: modelName.value, battery_type: batteryType.value, battery_quantity: Number(quantity.value), power_type: power.value });
      await this.refresh();
    });
    this.text(content, `Modely v katalógu: ${this.page?.total || 0} · sledované batériové zariadenia: ${this.page?.related?.tracked_device_count || 0} · evidované cykly: ${this.page?.related?.cycle_count || 0}`, "meta");
    this.items.forEach((item) => {
      const card = this.card(content, `${item.manufacturer || "Neznámy výrobca"} ${item.model || "Neznámy model"}`);
      this.text(card, `${item.default_battery_type || "Typ batérie neurčený"} × ${item.default_battery_quantity || 1} · zdroj: ${item.source || "lokálny"}`, "meta");
    });
    trackedDevices.forEach((device) => {
      const card = this.card(content, device.name || device.device_id);
      const estimate = device.battery_estimate;
      this.text(card, `${device.battery_type || "Typ neurčený"} × ${device.battery_quantity || 1} · posledná výmena: ${device.last_replaced_at || "nezaznamenaná"}`, "meta");
      this.text(card, estimate?.remaining_days_range ? `Odhad výdrže: ${estimate.remaining_days_range.join("–")} dní` : "Odhad výdrže zatiaľ nie je dostupný.", "meta");
      const actions = this.actions(card);
      const type = this.textInput(actions, "Typ batérie", device.battery_type || "");
      const quantity = this.numberInput(actions, "Počet", 1, 20, device.battery_quantity || 1);
      const power = this.select(actions, "Napájanie batérie", ["replaceable_battery", "rechargeable", "unknown"]);
      power.value = device.power_type || "replaceable_battery";
      const model = document.createElement("select");
      model.setAttribute("aria-label", "Model z katalógu");
      const noModel = document.createElement("option");
      noModel.value = "";
      noModel.textContent = "Bez väzby na model";
      model.append(noModel);
      this.items.forEach((item) => {
        const option = document.createElement("option");
        option.value = item.model_id;
        option.textContent = `${item.manufacturer || ""} ${item.model || ""} — ${item.default_battery_type || "?"} × ${item.default_battery_quantity || 1}`;
        model.append(option);
      });
      model.addEventListener("change", () => {
        const choice = this.items.find((item) => item.model_id === model.value);
        if (!choice) return;
        type.value = choice.default_battery_type || "";
        quantity.value = String(choice.default_battery_quantity || 1);
        if (["replaceable_battery", "rechargeable", "unknown"].includes(choice.power_hint)) power.value = choice.power_hint;
      });
      actions.append(model);
      this.button(actions, "Uložiť priradenie", async () => {
        const request = { type: "sensor_guardian/update_battery", device_id: device.device_id, battery_type: type.value, battery_quantity: Number(quantity.value), power_type: power.value };
        if (model.value) request.model_id = model.value;
        await this.command(request);
        await this.refresh();
      });
      if (device.manufacturer && device.model && !device.model_id) {
        this.button(actions, "Pridať predvyplnený model a priradiť", async () => {
          const added = await this.command({
            type: "sensor_guardian/add_model",
            manufacturer: device.manufacturer,
            model: device.model,
            battery_type: type.value,
            battery_quantity: Number(quantity.value),
            power_type: power.value,
          });
          await this.command({
            type: "sensor_guardian/update_battery",
            device_id: device.device_id,
            battery_type: type.value,
            battery_quantity: Number(quantity.value),
            power_type: power.value,
            model_id: added.model_id,
          });
          await this.refresh();
        });
      }
    });
    if (cycles.length) {
      const card = this.card(content, "Posledné výmeny");
      cycles.forEach((cycle) => this.text(card, `${cycle.device_id}: ${cycle.battery_type || "batéria"} × ${cycle.battery_quantity || 1}, ${cycle.started_at || "dátum neznámy"} · ${cycle.provenance || "bez zdroja"}`, "meta"));
    }
  }

  renderSettings(content) {
    const card = this.card(content, "Nastavenia a migrácia");
    const settings = this.page?.settings || {};
    const migration = this.page?.migration || {};
    this.text(card, `Úvodná tolerancia: ${settings.startup_grace_minutes ?? "predvolené"} min · upozornenie pred výmenou: ${settings.replacement_warning_days ?? "predvolené"} dní · nízka batéria: ${settings.low_battery_threshold ?? "predvolené"}%`, "meta");
    this.text(card, `Importy potvrdené: ${migration.receipt_count || 0} · nevyriešené záznamy na kontrolu: ${migration.unmatched_import_count || 0}`, "meta");
    const actions = this.actions(card);
    const grace = document.createElement("input");
    grace.type = "number";
    grace.min = "0";
    grace.max = "1440";
    grace.value = String(settings.startup_grace_minutes ?? 15);
    grace.setAttribute("aria-label", "Úvodná tolerancia v minútach");
    actions.append(grace);
    const warning = document.createElement("input");
    warning.type = "number";
    warning.min = "1";
    warning.max = "90";
    warning.value = String(settings.replacement_warning_days ?? 14);
    warning.setAttribute("aria-label", "Upozornenie pred výmenou v dňoch");
    actions.append(warning);
    const threshold = this.numberInput(actions, "Hranica nízkej batérie v percentách", 1, 100, settings.low_battery_threshold ?? 20);
    this.button(actions, "Uložiť nastavenia", async () => {
      await this.command({ type: "sensor_guardian/update_settings", values: {
        startup_grace_minutes: Number(grace.value),
        replacement_warning_days: Number(warning.value),
        low_battery_threshold: Number(threshold.value),
      }});
      await this.refresh();
    });
    this.button(actions, "Pripraviť náhľad Battery Notes", async () => {
      this.preview = await this.command({ type: "sensor_guardian/import_preview" });
      await this.refresh();
    });
    if (this.preview) {
      const preview = this.card(content, "Náhľad importu");
      const source = this.preview.source_available ? "Battery Notes je dostupný ako zdroj na jednorazový import." : "Battery Notes sa nenašiel; Strážca môže fungovať nezávisle.";
      this.text(preview, `${source} Katalóg: ${this.preview.catalogue_model_count}; párované zariadenia: ${this.preview.matched_device_count}; nevyriešené: ${this.preview.unmatched_count}; výmeny: ${this.preview.cycle_count}; vzorky: ${this.preview.sample_count}.`, "meta");
      this.text(preview, this.preview.history_note || "", "meta");
      if (this.preview.source_available) {
        const apply = this.actions(preview);
        this.button(apply, "Použiť tento import", async () => {
          await this.command({ type: "sensor_guardian/import_apply", receipt_id: this.preview.receipt_id });
          this.preview = null;
          await this.refresh();
        });
      }
    }
  }

  deviceActions(card, item) {
    const actions = this.actions(card);
    if (["battery_and_availability", "battery_only"].includes(item.tracking_mode) && item.power_type !== "mains") {
      this.button(actions, "Označiť výmenu batérie", async () => {
        const battery = window.prompt("Typ batérie (napr. CR2032)", "");
        if (battery === null) return;
        const quantity = Number(window.prompt("Počet batérií", "1") || 1);
        await this._hass.callService("sensor_guardian", "mark_battery_replaced", {
          device_id: item.device_id,
          battery_type: battery,
          battery_quantity: quantity,
        });
        this.status = "Výmena batérie je zaznamenaná.";
        this.paintStatus();
      });
    }
    this.button(actions, "Odložiť upozornenia", async () => {
      await this._hass.callService("sensor_guardian", "snooze_device", { device_id: item.device_id });
      await this.refresh();
    });
    this.button(actions, "Obnoviť upozornenia", async () => {
      await this._hass.callService("sensor_guardian", "resume_device", { device_id: item.device_id });
      await this.refresh();
    });
  }

  confirmCause(card, incidentId) {
    const actions = this.actions(card);
    const cause = this.select(actions, "Potvrdiť príčinu", ["unknown", "battery", "connectivity", "gateway_upstream", "integration", "power_or_network"]);
    this.button(actions, "Potvrdiť", async () => {
      await this._hass.callService("sensor_guardian", "confirm_incident_cause", { incident_id: incidentId, cause: cause.value });
      await this.refresh();
    });
  }

  async command(message) {
    try {
      const result = await this._hass.callWS(message);
      this.status = "Zmena bola uložená.";
      this.paintStatus();
      return result;
    } catch (error) {
      this.status = error.message || "Požiadavku sa nepodarilo dokončiť.";
      this.paintStatus();
      throw error;
    }
  }

  card(parent, title) {
    const card = document.createElement("article");
    card.className = "card";
    card.setAttribute("aria-label", title);
    this.text(card, title, "title");
    parent.append(card);
    return card;
  }

  text(parent, value, className = "meta") {
    const node = document.createElement("p");
    node.className = className;
    node.textContent = value;
    parent.append(node);
    return node;
  }

  badge(parent, value, problem = false) {
    const node = document.createElement("span");
    node.className = `badge${problem ? " problem" : ""}`;
    node.textContent = value;
    parent.append(node);
  }

  actions(parent) {
    const actions = document.createElement("div");
    actions.className = "actions";
    parent.append(actions);
    return actions;
  }

  button(parent, label, action) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = label;
    button.addEventListener("click", () => Promise.resolve(action()).catch(() => {}));
    parent.append(button);
    return button;
  }

  select(parent, label, values) {
    const select = document.createElement("select");
    select.setAttribute("aria-label", label);
    [...new Set(values)].forEach((value) => {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = this.label(value);
      select.append(option);
    });
    parent.append(select);
    return select;
  }

  textInput(parent, label, value = "") {
    const input = document.createElement("input");
    input.type = "text";
    input.value = value;
    input.placeholder = label;
    input.setAttribute("aria-label", label);
    parent.append(input);
    return input;
  }

  numberInput(parent, label, min, max, value) {
    const input = document.createElement("input");
    input.type = "number";
    input.min = String(min);
    input.max = String(max);
    input.value = String(value);
    input.setAttribute("aria-label", label);
    parent.append(input);
    return input;
  }

  empty(parent, message) {
    const node = document.createElement("p");
    node.className = "empty";
    node.textContent = message;
    parent.append(node);
  }

  label(value) {
    const names = {
      unknown: "neznáme",
      battery: "batéria",
      connectivity: "spojenie",
      gateway_upstream: "brána alebo nadradená sieť",
      integration: "integrácia",
      power_or_network: "napájanie alebo sieť",
      healthy: "v poriadku",
      degraded: "zhoršený stav",
      stale: "dlho bez hlásenia",
      offline: "nedostupné",
      recovering: "obnovuje sa",
      initializing: "inicializácia",
      battery_and_availability: "batéria aj dostupnosť",
      battery_only: "iba batéria",
      availability_only: "iba dostupnosť",
      replaceable_battery: "vymeniteľná batéria",
      rechargeable: "nabíjateľná",
      mains: "sieťové napájanie",
      high: "vysoká",
      medium: "stredná",
      low: "nízka",
      none: "žiadna",
    };
    return names[value] || String(value);
  }
}

if (!customElements.get("sensor-guardian-panel")) {
  customElements.define("sensor-guardian-panel", SensorGuardianPanel);
}
