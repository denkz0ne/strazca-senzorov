# Strážca senzorov: rozhranie pre prevenciu a diagnostiku

Stav: návrh na používateľské posúdenie. Existujúci produkčný frontend ani HA konfigurácia sa týmto dokumentom nemenia.

## Účel a podmienky úspechu

Strážca má predchádzať výpadkom batériových zariadení, ukázať aktuálne nedostupné zariadenia a zrozumiteľne vysvetliť pravdepodobnú príčinu. Dlhodobá história a predikcie majú pomôcť rozhodnúť, čo urobiť včas. Katalóg modelov, typy batérií a zásoby sú podporné informácie.

Po otvorení panelu používateľ zistí, čo potrebuje zásah teraz, čo je rizikové v najbližšom období a čo ešte nemožno spoľahlivo posúdiť. Detail každého problému poskytne pozorované fakty, odhad, mieru istoty a konkrétny ďalší krok.

Zachovávame slovenské rozhranie, kompaktné zoznamy, čitateľný názov/oblasť/ZB alebo ZBT označenie, zdrojovú integráciu a minimum HA entít. Battery Notes ostáva jednorazovým migračným zdrojom. Výmena frontendu nesmie stratiť už sledované zariadenia, výmenné cykly ani používateľské voľby.

## Zvolený prístup a alternatívy

Odporúčaný je dashboard s prioritami a spoločný detail zariadenia. Každá obrazovka používa tie isté stavové označenia a akcie. Nové zariadenia majú samostatný krátky postup pridania.

Alternatívou je jedna rozsiahla tabuľka s analytickými detailmi; zjednodušuje navigáciu, ale núti používateľa ručne vyhľadávať riziká. Druhou alternatívou sú oddelené analytické dashboardy pre batérie a dostupnosť; poskytujú viac priestoru grafom, ale rozdeľujú problém jedného zariadenia medzi obrazovky. Spoločný prioritný dashboard lepšie zodpovedá požadovanému každodennému používaniu.

## Navigácia

| Sekcia | Hlavná úloha |
| --- | --- |
| Prehľad | Aktuálne problémy, prevencia a kvalita sledovania |
| Zariadenia | Všetky sledované zariadenia, filtre a detail |
| Upozornenia | Aktívne/skupinové problémy, potvrdenie, odloženie a história |
| Pridať zariadenia (počet) | Nevyriešení noví kandidáti a bezpečné zapnutie sledovania |
| Nastavenia | Pravidlá integrácie, diagnostika, migrácia a doplnkové Batérie a zásoby |

Pri hlavnom menu zostávajú dostupné vyhľadávanie a filtre danej sekcie. Počty pri sekciách sa počítajú na serveri zo všetkých záznamov, nie iba z načítanej stránky.

Karta Zariadenia získava jasnú úlohu zoznamu sledovaných zariadení. Doterajší discovery zoznam sa presúva do Pridať zariadenia; už sledované a ignorované zariadenia sa v ňom naďalej neponúkajú.

## Prehľad

Horný pruh obsahuje stav zberu, poslednú úspešnú aktualizáciu a aktívnu verziu. Pod ním sú klikateľné súhrny: Nedostupné, Vyžadujú zásah, Riziko v nasledujúcich 14 dňoch, Učia sa / chýbajú údaje. Súhrny odkazujú na príslušný filtrovaný zoznam.

Najvýraznejšia časť je „Potrebuje zásah“. Zobrazuje aktívne nedostupné zariadenia, kritickú batériu a iné doložené problémy. Skupinový výpadok má jeden spoločný blok s počtom dotknutých zariadení a odkazom na detail. Zdravé zariadenia nepoužívajú výstražnú farbu.

Nasleduje „Skontrolovať čoskoro“: blížiaca sa výmena, prudký pokles úrovne, zhoršujúci sa signál a opakované krátke výpadky. Každé odporúčanie obsahuje dôvod a akciu. Nepodložený dátum výmeny sa nezobrazuje.

„Kvalita sledovania“ upozorní na chýbajúce zdroje, vypnutý odporúčaný signál, neznámy interval hlásení a príliš krátku históriu. Chýbajúce údaje sa nezamieňajú so zdravým zariadením.

V spodnej časti sú stručné trendy siete a posledné zmeny. Detailné grafy zostávajú v zariadení. Bez sledovaných zariadení sa zobrazí vysvetlenie a tlačidlo „Pridať zariadenia“, nie prázdna tabuľka.

## Zoznam a detail zariadenia

Kompaktný riadok obsahuje názov/ZB alebo ZBT, oblasť, integráciu, dostupnosť, prevádzkové riziko, batériu, odhadovaný interval zostávajúcej výdrže a čas posledného použiteľného hlásenia. Signál sa zobrazuje, ak existuje; inak sa vysvetlí, či je vypnutý alebo nepodporovaný.

Filtre: problémové, nedostupné, vyžadujúce výmenu, rizikové, neúplné údaje, oblasť, integrácia, transport a napájanie. Výsledky sú stránkované a triedené na serveri; export ani súhrny nesmú pracovať len s aktuálnou stránkou.

Kliknutie otvorí plnohodnotný detail s návratom na pôvodné filtre/pozíciu:

1. **Stav a odporúčanie:** najdôležitejší problém, posledné známe údaje a ďalšia akcia.
2. **História:** batériové percentá/napätie a výmeny, dostupnosť/výpadky, signál podľa skutočne dostupných dát. Intervaly 7/30/90 dní; chýbajúce úseky sa nevyplnia domyslenými hodnotami.
3. **Predikcia:** interval výdrže, trend, porovnanie vlastných cyklov, počet vzoriek, pokryté obdobie a dôvody miery istoty.
4. **Diagnostika:** dôkazy pre a proti možnej príčine, zdieľaný problém, čo nemožno potvrdiť a odporúčané overenie.
5. **Nastavenia:** režim sledovania, napájanie, prahy, upozornenia, voliteľná kritickosť a pokročilý výber zdrojov. Typ/počet batérií je jednoduchý doplnkový údaj.

Bežné akcie sú dostupné pri súvisiacom údaji: Zaznamenať výmenu, Potvrdiť príčinu, Odložiť upozornenie, Upraviť sledovanie. Zmena nastavení nepotrebuje odstránenie a opätovné pridanie zariadenia.

Pozastavenie sledovania uchová históriu. Vymazanie histórie je samostatná potvrdená operácia so zálohou. Akcia odloženia upozornenia nesmie zastaviť zbieranie dát.

## Upozornenia a diagnostika

Upozornenie odpovedá: ktoré zariadenie alebo skupina, čo sa stalo, odkedy, pravdepodobná príčina, podklady, neistota a odporúčaný zásah.

Príklady vhodných textov:

- „Batéria klesla o 12 bodov za 3 dni. Pokles je rýchlejší než v predchádzajúcom cykle. Skontroluj batériu.“
- „Zariadenie je nedostupné v HA. Posledná použiteľná batéria bola 4 %. Príčina sa ešte nedá potvrdiť.“
- „Súčasne vypadlo viac zariadení zo spoločného zdroja. Skontroluj dostupnosť integrácie/brány.“

Pozorované fakty a odhad príčiny sú vizuálne oddelené. Bodové skóre interných pravidiel sa nezobrazuje ako percentuálna pravdepodobnosť. Príčina „Neznáma“ obsahuje vysvetlenie chýbajúcich alebo konfliktných dôkazov.

Skupinové upozornenia potláčajú duplicitné jednotlivé oznámenia; počty zariadení sa nedvojnásobia. Potvrdenie prečítania neznamená vyriešenie. Upozornenie sa uzatvára pri stabilnej obnove alebo korektnom vypnutí sledovania s príslušným dôvodom.

Pravidlá upozornení zahŕňajú závažnosť, časovú toleranciu, odloženie, opakovanie pri nezmenenom probléme a tiché hodiny. Kritickosť zariadenia je explicitná používateľská voľba; systém ju neodhaduje z názvu. Natívne HA upozornenia a udalosti pre automatizácie zostávajú dostupné.

## Pridanie nových zariadení

Nové vhodné zariadenie aktualizuje čakajúci počet bez automatického sledovania. Postup je:

Počet je viditeľný pri sekcii Pridať zariadenia a v jednom natívnom HA upozornení. Nepredpokladáme nepodporovaný číselný odznak pri vlastnej položke v HA sidebare.

1. **Vybrať:** kandidáti podľa názvu/oblasti/integrácie, jednotlivý alebo hromadný výber.
2. **Skontrolovať odporúčanie:** režim, napájanie, použiteľné merania a prípadné chýbajúce údaje sú predvyplnené osobitne pre každý riadok.
3. **Potvrdiť:** stručný súhrn toho, čo sa bude sledovať a prípadne zapínať. Typ batérie možno doplniť neskôr; dostupnosť nečaká na katalóg.
4. **Výsledok:** jasný stav každého zariadenia — sleduje sa, dokončuje sa nastavenie, vyžaduje opravu alebo bolo ignorované. Čiastočný neúspech má konkrétny dôvod a bezpečné opakovanie.

Jednoduchý kandidát prejde jednou spoločnou kontrolnou obrazovkou; štyri kroky predstavujú logické fázy, nie povinné štyri kliknutia pre každé zariadenie.

Hromadné pridanie musí znovu overiť všetky kandidátske zdroje pred zápisom, ukladať výsledok operácie a byť idempotentné. Zlyhanie jedného riadka sa nesmie prezentovať ako úspech celej skupiny. Ignorovanie prežíva reštart; zmena HA identity vytvára nového kandidáta.

Odporúčané signálové entity sa zapínajú len po explicitnom súhlase pre označené zariadenia. Úplne chýbajúce údaje vedú k upozorneniu „nedostatočné pokrytie“, nie k vymyslenej diagnostike.

## Nastavenia a doplnkové batérie

Integrácia má rozumné predvolené pravidlá prevencie, časové tolerancie, prahy batérie, horizont preventívnych upozornení, históriu/retenciu a pravidlá doručenia. Zariadenie môže mať vlastnú výnimku; UI ukáže, ktoré pravidlo je zdedené a ktoré bolo prepísané.

Nastavenia zariadenia sú v jeho detaile. Spoločné pravidlá sú v Nastaveniach integrácie. Prevádzkové informácie obsahujú aktívnu verziu backendu/frontendu, stav zberu, pokrytie dát, stav migrácie a anonymizovaný export diagnostiky.

„Batérie a zásoby“ je doplnková časť: súhrn najpoužívanejších typov, kusy v sledovaných zariadeniach, skutočné výmeny v období, ručne evidovaná zásoba a odporúčaná rezerva. Počty použitých kusov vychádzajú z potvrdených výmen; obsah katalógu sa nepočíta ako spotreba.

Odporúčanie zásoby využíva doloženú vlastnú spotrebu a blížiace sa výmeny. Bez použiteľnej histórie sa zobrazí vysvetlené pomocné pravidlo alebo používateľská minimálna rezerva. Nabíjanie sa nepočíta ako spotreba novej batérie. Neznáme typy sú oddelené; údaje pokrývajú sledované zariadenia, nie neznámy celkový počet zariadení v domácnosti.

## Dáta, dlhodobé učenie a predikcie

Frontend nebude sám počítať diagnostické skóre ani odhadovať výdrž z aktuálneho percenta. Backend poskytuje stabilné súhrny, kvalitu a dôvody.

Potrebné rozšírenia existujúceho backendu:

- Súhrn všetkých sledovaných zariadení a poradie zásahov; oddeliť dostupnosť, preventívne riziko a kvalitu dát.
- Dátovaná história signálu a prechodov dostupnosti, ktoré sú dnes neúplné. Opakované nezmenené vyhodnotenia nevytvárajú nové prechody.
- Grafové časové série a agregácie s medzerami, kvalitou a pôvodom; dlhodobé ukladanie do Strážcu a ohraničená retencia.
- Voliteľné jednorazové doplnenie dostupnej histórie pôvodných HA entít z Recorder; bez domyslenia vymazaných dát a bez runtime závislosti na Battery Notes.
- Kombinácia trendu aktuálneho batériového cyklu, vlastných výmenných cyklov, prudkého poklesu, stálosti/kolísania signálu a opakovaných výpadkov.
- Vysvetlenie, prečo odhad zatiaľ neexistuje, a stav učenia. Každý odhad má interval, mieru istoty, vstupné obdobie a dôvody.

Rozlišujeme čas zápisu stavu do HA, posledné použiteľné meranie a skutočný rádiový report, ak ho provider spoľahlivo poskytuje. Obnovený/uložený stav ani pravidelné cloudové dotazovanie sa nesmú automaticky považovať za nový fyzický report.

Senzor, ktorý reportuje iba pri udalosti, nemôže byť označený za offline len preto, že nikto neprešiel okolo. Vybitá batéria a slabé spojenie sú hypotézy s konkurenčnými dôkazmi; ak nestačia, výsledok ostáva neznámy.

Pravidlá signálu rešpektujú jednotky a možnosti zdrojovej integrácie. LQI sa neprezentuje ako univerzálne porovnateľné percento. Nízkymi údajmi nepotvrdený odhad nevyvolá červený alarm s predstieraným presným termínom.

## Rozhrania a technické hranice

Zachováme doménu, existujúce unique ID HA entít, actions a udalosti pre automatizácie. Podrobné štatistiky zostávajú interné; nepribúdajú predvolené entity pre každý graf.

Existujúci vlastný panel sa rozdelí na bootstrap, navigáciu, zdieľané prvky a samostatné pohľady/detail/pridanie. Použije HA farby/tému a lokálne zabalené moduly bez runtime CDN. Výmena rendereru nesmie prerušiť registrovanú URL panelu.

Navrhované admin-only WS rozhrania: get_dashboard, get_device_detail, get_alerts, preview_tracking, apply_tracking a aktualizácie pravidiel/zásob. Aktuálne get_data a existujúce write príkazy zostávajú kompatibilné. Servery validujú vstup, zdrojové väzby a operácie; browser neuchováva trvalý stav.

Dashboard vracia súhrny nad celým súborom dát, zatiaľ čo zoznamy a časové série sú obmedzené stránkou/obdobím. Formuláre chránia rozpracované zmeny pred auto-refreshom; sieťová chyba má retry a nezamlčí, že údaje sú staré.

Nové historické dáta a nastavenia vyžadujú verzovanú migráciu s predchádzajúcou zálohou, zachovaním doterajších cyklov/vzoriek a testom opakovaného načítania. Retencia dát a reset profilu sú odlišné od odstránenia zariadenia.

Podpora sťahuje anonymizované dáta. Prevádzkový panel musí ukázať skutočne aktívnu verziu; úspešné CI ani zlúčený PR nepredstavujú overenie nainštalovanej HA verzie. HACS musí sledovať predvolenú main vetvu.

## Vizuál a interakcie

Dashboard kombinuje malé súhrnné karty a kompaktné prioritné zoznamy. Dlhé tabuľky sú pre správu zariadení; detailné grafy majú os/obdobie/jednotky a vysvetlenie. Farba dopĺňa text/ikonu, nenahrádza význam.

Desktop má prehľad a detail vedľa seba, ak šírka dovolí. Na mobile detail zaberá jednu stránku a hlavné údaje sú dostupné bez vodorovného rolovania; pokročilé tabuľky môžu mať vlastný posun. Ovládanie je dostupné klávesnicou, detail obnovuje focus a tlačidlá majú jednoznačné názvy.

## Akceptačné scenáre

1. Nový používateľ vie pridať bežné batériové zariadenie bez znalosti registry ID a bez povinného katalógového modelu.
2. Percento batérie sa zobrazí hneď, keď existuje platný zdroj. Chýbajúci ETA ukazuje konkrétny dôvod; chýbajúca batéria sa neprevedie na 0 %.
3. Pri nedostupnej hlavnej entite zásuvky nedokáže uložená energetická telemetria skryť výpadok.
4. Pri slabej diagnostike zostáva príčina neznáma s vysvetlením. Systém nepriradí rádiový report obnovenému HA stavu.
5. Skupinový výpadok sa oznámi raz; zmena členov, stabilná obnova a vypnutie sledovania korektne upravia upozornenia.
6. Hromadné pridanie rešpektuje každý riadok, jasne oznámi čiastočný výsledok a opakovanie neduplikuje zariadenia.
7. Upozornenie na prudký pokles môže vzniknúť pred ETA; trend ani predikcia neprepája odlišné batériové cykly.
8. Auto-refresh nevymaže formulár, rozbalený detail ani výber. Súhrny a filtre fungujú nad celým datasetom.
9. Zásoby odrážajú potvrdenú spotrebu a ukazujú kvalitu podkladov; katalógové riadky sa nevydávajú za spotrebu.
10. Staré tracked zariadenia/cykly/entity ID prežijú migráciu. Živé HA overenie potvrdí aktívnu verziu a celý postup od discovery po upozornenie.

## Poradie dodania

Najprv dátové kontrakty, kvalita pozorovaní, historické dáta a prioritné súhrny. Potom nový Prehľad, Zariadenia a spoločný detail, ktoré používajú tieto kontrakty. Následne ucelený postup pridania, upozornenia a nastavenia. Doplnkové zásoby sa dokončia po funkčnej prevencii a diagnostike.

Každá časť má overiteľný používateľský scenár, automatické HA/API/Chromium testy primerané zmene a následnú kontrolu nainštalovanej verzie na HA. Tento dokument určuje návrh; samostatný implementačný plán vznikne po jeho posúdení.
