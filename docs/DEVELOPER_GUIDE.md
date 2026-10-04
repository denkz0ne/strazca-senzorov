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

Write commands implementované teraz: `import_preview`, `import_apply`, `track_device`, `dismiss_candidate`, `update_settings`, `add_model`, `update_battery`. Každý nový command potrebuje schému, autorizáciu, bounds/ID kontroly, persistence ordering, odpoveď/error a WebSocket test. Panel nesmie byť zdrojom trvalého stavu.

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
