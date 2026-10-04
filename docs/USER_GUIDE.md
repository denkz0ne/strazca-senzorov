# Používateľský návod

Tento návod opisuje aktuálnu vývojovú verziu Strážcu senzorov. Projekt zatiaľ nemá stabilné vydanie; názvy a umiestnenie položiek sa môžu medzi verziami meniť. Ak sa správanie v tvojej HA inštalácii líši od návodu, rozhodujúce je správanie konkrétnej verzie a treba ho nahlásiť podľa [podpory a riešenia problémov](#riešenie-problémov).

## Čo sa zobrazí po prvom spustení

Panel sa dá používať bez konfigurácie integrácie. Karta **Zariadenia** vyhľadá kandidátov z HA registrov a zobrazí ich návrh sledovania. Samotné objavenie zariadenia ho ešte nezačne sledovať.

- **Prehľad** zostane prázdny, kým aspoň jedno zariadenie nezačneš sledovať.
- **Zariadenia** obsahujú objavené kandidáty. Skontroluj režim a typ napájania, potom vyber **Sledovať** alebo **Ignorovať**.
- **Batérie** zobrazujú katalóg a údaje o sledovaných batériových zariadeniach. Modelový predvolený typ batérie je len návrh; uprav ho podľa skutočne vloženej batérie.
- **Incidenty** sa naplnia až po spracovaní problému u sledovaného zariadenia.
- **Nastavenia** obsahujú momentálne podporované prahy a stav importu.

Panel môže v tejto verzii ukazovať interné ID zariadenia namiesto jeho mena. Pred výberom preto porovnaj navrhnuté entity a ich názvy. Toto je známe obmedzenie úvodného discovery UI.

Kompaktné tabuľkové zoznamy, hromadný výber a filtre, zobrazenie pôvodnej HA integrácie v Prehľade, upozornenie na nové kandidáty a ukotvenú navigáciu pri scrollovaní riešia budúce požiadavky [#11](https://github.com/denkz0ne/strazca-senzorov/issues/11), [#12](https://github.com/denkz0ne/strazca-senzorov/issues/12), [#13](https://github.com/denkz0ne/strazca-senzorov/issues/13) a [#14](https://github.com/denkz0ne/strazca-senzorov/issues/14); zatiaľ ich panel nemusí zobrazovať.

## Začni s jedným zariadením

1. Otvor **Zariadenia** a vyhľadaj kandidáta podľa názvu alebo entity.
2. Skontroluj dostupné dôkazy: batériová úroveň, `battery low`, napätie, dostupnosť alebo signál. Vypnuté signálové entity sú iba odporúčané; Strážca ich sám nezapne.
3. Vyber režim:
   - **Batéria aj dostupnosť** pre batériové zariadenie, ktoré chceš monitorovať oboma spôsobmi.
   - **Iba batéria** ak ťa zaujíma batéria a zariadenie nemá spoľahlivý pravidelný report.
   - **Iba dostupnosť** pre sieťovo napájané zariadenie alebo zariadenie bez batériových údajov.
4. Vyber typ napájania. Pri batériovom režime skontroluj alebo nastav typ a počet batérií v karte **Batérie**.
5. Stlač **Sledovať**. Zariadenie sa objaví v **Prehľade**; pri problémoch sa môže vytvoriť incident.
6. Nevyberaj hromadne všetkých kandidátov naraz. Najprv over niekoľko reprezentatívnych zariadení a správnosť zdrojových entít.

**Ignorovať** skryje kandidáta z aktuálnych odporúčaní. Nie je to vypnutie zdrojových HA entít.

## Čo znamenajú stavy a odhad príčiny

Stav zdravia a pravdepodobná príčina sú samostatné informácie. Strážca používa `initializing`, `healthy`, `degraded`, `stale`, `offline`, `recovering`, `paused` a `unknown`. Presné prahy závisia od naučeného reportovacieho profilu a explicitnej dostupnosti zdroja.

Príčiny môžu byť `battery`, `connectivity`, `gateway_upstream`, `integration`, `power_or_network` alebo `unknown`. `unknown` znamená, že podklady nestačia alebo si odporujú. Body v diagnostike sú interné dôkazové body, nie percentuálna pravdepodobnosť.

`last_reported` znamená, že integrácia zdrojovej entity zapísala jej stav. Samo osebe nedokazuje, že zariadenie práve vysielalo cez rádio. Ak integrácia publikuje uložený stav, Strážca to nemusí vedieť rozlíšiť bez špecifického adaptéru.

## Batérie a výmena

- Katalóg zariadení poskytuje model a typ/počet batérií, nie garantovanú životnosť.
- Odhad sa učí z úrovní batérie a výmen na konkrétnom zariadení. Pri málo dátach môže byť odhad prázdny alebo nízkej dôveryhodnosti.
- Skok úrovne batérie môže byť iba kandidát na výmenu. Potvrď výmenu až po fyzickej výmene.
- Nabitie nabíjateľnej batérie sa neeviduje ako výmena.
- Pri sieťovom napájaní sa batériové odhady nepoužívajú.

Použi akciu `sensor_guardian.mark_battery_replaced` po výmene, aby sa zaznamenal nový cyklus a voliteľne typ, počet, značka a dôvod. Akcia je idempotentná pre rovnaký záznam výmeny.

## Jednorazový import Battery Notes

Battery Notes slúži iba ako migračný zdroj. V **Nastavenia** otvor náhľad importu, skontroluj spárované a nevyriešené zariadenia, rekonštruované cykly a neisté dáta, potom import aplikuj. Import najprv vytvorí oddelenú zálohu a ukladá potvrdenie o zdroji. Opakovaný import nemá duplikovať rovnaké záznamy.

Battery Notes odstráň až po tom, čo skontroluješ výsledok importu, zariadenia a výmeny batérií v Strážcovi a overíš chod po reštarte. Strážca ho sám neodinštaluje a po importe ho nepotrebuje.

## Automatizácie

Každé sledované zariadenie vytvára najviac tri Strážca entity: `guardian_problem`, `guardian_status` a pri batériovom sledovaní aj `battery_attention`. Vytváranie entít prebieha až po výbere sledovania. Názvy entít si pozri v **Nastavenia → Zariadenia a služby → Entity**; konkrétne ID vytvorí HA podľa mena a kolízií v registri.

Strážca vysiela udalosti `sensor_guardian_incident`, `sensor_guardian_recovered`, `sensor_guardian_battery_attention` a `sensor_guardian_battery_replaced`. Akcie sú dostupné pod doménou `sensor_guardian`: `mark_battery_replaced`, `confirm_incident_cause`, `snooze_device` a `resume_device`. Kompletné polia a príklady sú v [rozhraní Home Assistant](HOME_ASSISTANT.md).

## Záloha, aktualizácia a návrat

Pred aktualizáciou HA vytvor zálohu HA vrátane konfigurácie a úložiska. Pri aktualizácii vlastnej integrácie zachovaj celý adresár `custom_components/sensor_guardian`; po výmene súborov reštartuj Home Assistant a skontroluj logy. Neukladaj používateľské dáta ručne do súborov integrácie. Persistované dáta spravuje Strážca cez HA Store.

Ak aktualizácia zlyhá, najprv zachovaj HA zálohu a logy. Vráť predchádzajúcu verziu integrácie z tej istej dôveryhodnej vetvy/commitu a reštartuj. Nevymazávaj `.storage` ani záznamy integrácie ako prvý krok.

## Riešenie problémov

1. Over, že priečinok `custom_components/sensor_guardian` obsahuje `manifest.json` a `www/panel.js`.
2. V **Nastavenia → Systém → Logy** vyhľadaj `sensor_guardian` a skopíruj prvú súvisiacu chybu aj traceback.
3. Obnov panel a skontroluj, či si v správnej karte. Prázdny **Prehľad** je očakávaný, ak ešte nič nesleduješ.
4. Ak zariadenie nemožno sledovať, obnov **Zariadenia** a over, že kandidát stále existuje a HA device registry ho ešte obsahuje.
5. Pri chýbajúcich štatistikách over, či existujú použiteľné zdrojové entity a či má zariadenie dostatočnú históriu. Príčina `unknown` je očakávaná pri nedostatku dôkazov.
6. Pri chybe importu zachovaj pre-import zálohu; neprerušuj ho vymazaním Battery Notes ani úložiska.

Pri nahlásení problému pridaj verziu Strážcu z `manifest.json`, Core verziu, vetvu/commit, kroky na reprodukciu, relevantný log a očakávaný/skutočný výsledok. Pred zdieľaním odstráň tokeny, adresy a osobné dáta.
