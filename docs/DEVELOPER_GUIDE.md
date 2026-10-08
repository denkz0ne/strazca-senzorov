# Vývojársky návod

Tento dokument popisuje implementáciu v `custom_components/sensor_guardian`, nie iba cieľovú architektúru. Pri rozpore so zdrojovým kódom platí aktuálny kód; zmenu rozhrania treba následne zachytiť v tejto dokumentácii a v [changelogu](../CHANGELOG.md).

## Požiadavky a lokálne kontroly

- Python 3.14 podľa aktuálneho GitHub Actions workflow.
- Home Assistant Core 2026.9 ako počiatočná hranica podpory; release ešte vyžaduje samostatný kompatibilitný beh na minime a aktuálnom Core.
- Testovacie závislosti: `python -m pip install -r requirements_test.txt`.
- Kontroly: `ruff check .`, `node --check custom_components/sensor_guardian/www/panel.js`, parsovanie `hacs.json`/`manifest.json` a `pytest -q`.
- Pytest autoritatívne beží na Linuxe v GitHub Actions. Home Assistant test závislosti používajú POSIX API a v natívnom Windows prostredí sa nemusia spustiť.

## Mapa balíka

| Cesta | Zodpovednosť |
| --- | --- |
| `__init__.py`, `runtime.py` | Setup/unload, koordinácia, listener lifecycle, spracovanie zariadení |
| `config_flow.py`, `const.py` | Jediný globálny config entry a identita integrácie |
| `models.py`, `storage.py`, `migrations.py` | Typované záznamy, validácia a HA Store schema |
| `discovery.py` | Kandidáti z HA registrov, entity signály a odporúčanie sledovania |
| `sources.py`, `diagnostics.py` | Idempotentná oprava pôvodných zdrojov, verzia väzby a anonymizované pokrytie dôkazov |
| `availability/` | Reportovací profil, zber dôkazov dostupnosti a health transitions |
| `battery/` | Zber/normalizácia vzoriek, životné cykly a odhad výdrže |
| `diagnosis/` | Normalizované dôkazy, score pravidlá, zdieľané závislosti a incidenty |
| `migration/battery_notes.py` | Izolovaný preview/apply a obnova jednorazového importu |
| `binary_sensor.py`, `sensor.py`, `services.py`, `events.py` | Malý HA entity/action/event kontrakt |
| `websocket_api.py`, `panel.py`, `www/panel.js` | Administrátorský panel, HTTP static asset a WS API |
| `data/battery_models.json` | Lokálna verzovaná kópia premeneného modelového katalógu |

Podrobnosti komponentov sú v [architektúre](ARCHITECTURE.md), [dátovom modeli](DATA_MODEL.md), [dostupnosti](AVAILABILITY.md) a [paneli](FRONTEND.md).

## Konfiguračný a runtime lifecycle

Integrácia má `single_config_entry: true`; config flow nežiada polia. Setup načíta a validuje verzované dáta, jednorazovo doplní chýbajúce zabalené modely, registruje panel/WS API/akcie, načíta existujúce sledované entity a prihlási filtrovaných listeners iba na zvolené entity. Unload odregistruje listeners/platformy a odložené zápisy.

Kandidáti discovery nie sú tracked devices. Tracked record vzniká až po explicitnom `track_device`; vtedy Strážca uloží zdrojové entity, tracking mode, power type a modelové/batériové voľby a vytvorí minimálne HA entity.

## Storage kontrakt

`GuardianStorage` používa HA `Store` s major verziou `1` a minor `1` a uloženie na entry-scoped kľúč. Payload kolekcie: `models`, `devices`, `samples`, `cycles`, `availability_profiles`, `dependencies`, `incidents`; koreň obsahuje aj `settings`. Validátor vyžaduje stabilné string ID v každej kolekcii a objekty nastavení. Migrácie sú explicitné; nevalidné payloady sa automaticky neukladajú a novšia nepodporovaná minor schéma sa odmietne. Exportovaný envelope nezverejňuje interný HA storage kľúč.

Nová perzistentná kolekcia alebo zmena významu záznamu vyžaduje: úpravu TypedDict/validátora, safe migráciu, testy starej i novej schémy a úpravu `DATA_MODEL.md`, `PROGRESS.md` a changelogu. Nikdy nemaž neznáme extension polia bez zdokumentovanej migrácie.

## Observation a diagnostické hranice

- Zdrojom pravdy sú existujúce HA entity a device/entity registry metadata. Strážca nekomunikuje priamo s rádiami.
- Listener `state_reported` musí mať úzky zoznam sentinel ID. Nepoužívaj globálny listener.
- `last_reported` je čas zápisu HA zdrojovou integráciou, nie nevyhnutne čas fyzického prenosu zariadenia.
- Zdravotný stav a príčina výpadku sú samostatné výstupy.
- Príčiny a ich skóre musia mať dohľadateľné dôkazy; skóre nie je pravdepodobnosť. Pri nízkom skóre alebo tesnom rozpore vráť `unknown`.
- Korelácia podľa zdieľaného transportu/config entry bez potvrdeného fyzického dependency vzťahu nesmie predstierať presnú diagnózu.

## Panel/WebSocket API

Všetky príkazy používajú prefix `sensor_guardian/`, kontrolujú administrátorské oprávnenie a validujú vstup. Read command `get_data` vyberá jednu sekciu (`overview`, `batteries`, `devices`, `discovery`, `incidents`, `settings`) a obmedzenú stránku. Serializéry majú allow-list polí; nezverejňuj celý storage payload.

Write commands implementované teraz: `import_preview`, `import_apply`, `track_device`, `dismiss_candidate`, `update_settings`, `add_model`, `update_battery`, `update_tracking`, `enable_signal_entities`. Každý nový command potrebuje schému, autorizáciu, bounds/ID kontroly, persistence ordering, odpoveď/error a WebSocket test. Panel nesmie byť zdrojom trvalého stavu.

`update_tracking` prijíma device_id, tracking_mode a power_type; zachováva existujúce záznamy/unique ID a ukladá explicitné voľby do user_overrides. `enable_signal_entities` prijíma device_id a znovu overuje odporúčania v natívnom registri; zapína iba aktuálne vypnuté signálové entity priradené danému sledovanému zariadeniu.

Binding version 2 sa prehodnocuje zo zdrojových registrov pri štarte a zmenách registrov. Pred opravou legacy väzieb sa uloží samostatný Store `sensor_guardian.pre_source_repair.<entry_id>`; nejde o zmenu koreňovej schémy 1.1. Battery Notes a Strážca helper entity sa nepoužívajú ako runtime zdroje. Pri zmene kanonického reportovacieho zdroja sa obnoví jeho availability profil; vzorky a výmenné cykly sa zachovávajú.

GitHub CI teraz používa aj Chromium interakcie panelu: `cd tests/frontend`, `npm ci`, `npx playwright install chromium`, `npm test`. Testuje percentá, hromadné odporúčania, úpravy sledovania, zapnutie signálu a úzke zobrazenie na simulovanom HA rozhraní. Tieto testy nenahrádzajú kontrolu po inštalácii na živom HA.

## Kompatibilita HA entity/action/event

Helper entity sa pripájajú k pôvodnému device cez podporované `async_entity_id_to_device`; nepridávaj Strážca config entry do zariadenia cudzej integrácie. Udržiavaj počet a atribúty entít malé. Názvy akcií, event payloadov a verzie sú verejný kontrakt: zmenu dokumentuj a zachovaj spätnú kompatibilitu alebo zvýš payload/schema verziu.

## Vydanie, verzovanie a hotfix

Verzia integrovanej distribúcie je `custom_components/sensor_guardian/manifest.json:version`. Pred vydaním:

1. Skontroluj otvorené otázky, compatibility floor a release checklist.
2. Aktualizuj `CHANGELOG.md` s používateľsky viditeľnou zmenou, migráciou a prípadným breaking change.
3. Zosúlaď README, používateľský/vývojársky návod, dátový model a HA kontrakt podľa zmenených rozhraní.
4. Zvýš manifest verziu podľa dopadu: patch pre kompatibilnú opravu, minor pre kompatibilnú funkcionalitu, major pre nekompatibilný kontrakt alebo migráciu, ak projekt neustanoví inú politiku.
5. Aktualizuj release checklist a progress s presnými CI run/commit odkazmi. Nevydávaj tag bez explicitného rozhodnutia maintainer-a.

Hotfix musí zdokumentovať: symptom a dopad, reprodukčné kroky alebo dôkaz, príčinu, minimálnu opravu, riziko migrácie/dát, testy/CI run a verziu hotfixu. Po nasadení doplň konkrétny výsledok zo skutočnej HA inštalácie; CI samo osebe nie je dôkaz live opravy.

## Prevention API and frontend (0.2.0)

Added modules: history, analytics, onboarding, prevention_api, notification_policy and www/frontend/*.js. Legacy entities/actions and get_data remain compatible. Admin-only WebSocket additions:

| Read commands | Mutations |
| --- | --- |
| get_dashboard, get_devices, get_device_detail (7/30/90 days) | preview_tracking → apply_tracking |
| get_alerts (active/closed), get_candidates | save_settings, update_device_rules, set_tracking_active |
| get_settings, get_stock, get_diagnostics | acknowledge_alert (minutes=0 read / >0 snooze), save_stock |
| device detail native source choices | update_sources, reset_report_profile, load_native_history |

Lists return bounded pages (query/offset/limit); detail exposes actual series/cycles/source choices and a rule allow-list. Cross-device/helper source overrides are rejected. Settings reject invalid ranges/quiet-hours pairs. Nullable device rule fields remove overrides and inherit global values. Tracking previews last 15 minutes and accept at most 100 IDs; source fingerprint changes block the entire batch before insertion. Pending receipts contain consented signal changes and retry completion after a failure. No unconsented disabled entity is enabled.

Browser regression: `cd tests/frontend && npm ci && npx playwright install chromium && npm test`. The test serves actual packaged modules against mocked HA responses. Python/HA authoritative tests run in GitHub Actions/Linux/Python 3.14; Windows checks cannot replace this. Never claim owner installation from CI. Always compare HACS installed/available ref, panel/backend version and fresh owner logs before reporting live success.
