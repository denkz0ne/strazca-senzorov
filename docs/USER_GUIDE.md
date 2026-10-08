# Používateľský návod — 0.2.0

Strážca pomáha predísť výpadku batériového zariadenia, nájsť nedostupné zariadenia a vysvetliť pravdepodobnú príčinu. Stav HA, batériové údaje a istota odhadu sú samostatné informácie. Chýbajúca hodnota nie je nula ani potvrdenie správnej funkcie.

## Aktualizácia cez HACS

1. Zálohuj konfiguráciu HA a exportuj údaje Strážcu cez Nastavenia → Jednorazový import a zálohy.
2. V HACS otvor repozitár `denkz0ne/strazca-senzorov`. Použi predvolenú vetvu `main` a aktualizuj alebo znovu stiahni integráciu.
3. Reštart vykonaj sám cez HA. Potom obnov stránku panelu.
4. V Nastaveniach over frontend aj backend **0.2.0**, schému **1.2** a čas posledného vyhodnotenia. Rozdiel verzií panel oznamuje.
5. Skontroluj jedno známe batériové a jedno sieťové zariadenie. Porovnaj batériu/signál s pôvodnými HA entitami. Over, že zostali zariadenia, výmeny a história.

Pred prvou migráciou staršej schémy sa vytvorí interná záloha. Zálohy schémy 1.1 možno obnoviť do 1.2. Kódové a prehliadačové kontroly na GitHube nenahrádzajú tento krok na tvojej HAOS inštalácii.

## Prehľad

Úvodný dashboard má súhrny nedostupných zariadení, potrebných zásahov, prevencie a kvality údajov. Najprv ukazuje zariadenia vyžadujúce zásah, potom preventívne odporúčania, chýbajúce údaje a posledné zmeny dostupnosti. Kliknutím otvoríš príslušný zoznam alebo detail.

- **Nedostupné:** stav vybraných zdrojov alebo vyhodnotené chýbajúce hlásenia.
- **Zásah:** nízka batéria, rýchly pokles alebo zhoršená dostupnosť.
- **Prevencia:** podložený interval výmeny alebo zhoršujúci sa signál. Horizont sa dá upraviť globálne aj pre zariadenie.
- **Kvalita údajov:** chýbajúci zdroj, nenaučený interval, málo histórie alebo vypnutý signál. Dostupná HA hodnota sama osebe neznamená naučený reportovací profil.

Spoločný výpadok sa zobrazuje ako jedna skupina; počet nedostupných zariadení počíta každé zariadenie iba raz.

## Zariadenia a detail

Zoznam obsahuje iba sledované zariadenia. Má vyhľadávanie, filtre a stránkovanie. Zobrazuje názov z HA, oblasť, pôvodnú integráciu, napájanie, dostupnosť, batériu a signál. Označenie ZB/ZBT sa vyberá z názvu; ak chýba, ostane prázdne. Na mobile sa riadky menia na kompaktné karty.

Detail zobrazuje stav, odporúčanie, čas batériového pozorovania, interval výdrže a jeho istotu. Grafy ponúkajú 7/30/90 dní skutočných pozorovaní batérie, napätia, signálu a dostupnosti. Nevymýšľajú merania v medzerách. Zaznamenané výmeny oddeľujú batériové cykly. Starší údaj je označený ako posledný známy; po potvrdenej výmene sa čaká na nový údaj, nie na percento starej batérie.

V detaile môžeš upraviť režim sledovania, napájanie, prahy a kritickosť. Prázdny individuálny prah dedí globálne nastavenie. Pozastavenie zachová históriu; obnovenie vracia pôvodný režim. Pokročilé zdroje umožňujú vybrať iba vhodné natívne entity daného zariadenia alebo obnoviť automatický výber. Reset reportovacieho profilu nemaže výmeny ani batériovú históriu.

**Výmenu zaznamenaj až po fyzickej výmene.** Nabíjanie nie je výmena. Typ a počet batérií sú pomocné informácie pre zásoby. Odhad výdrže vzniká z reportov a cyklov konkrétneho zariadenia, nie zo všeobecnej životnosti CR2032.

## Upozornenia

Sekcia obsahuje aktívne alebo aj uzavreté problémy, dôkazy a postihnuté zariadenia. Batériový problém je nezávislý od dostupnosti. Neznáma príčina znamená nedostatočné alebo protichodné dôkazy; potvrdenú príčinu dostupnosti môžeš zaznamenať ručne.

- **Potvrdiť prečítanie:** zastaví opakovanie aktuálneho upozornenia.
- **Odložiť:** dočasne odloží doručenie; po uplynutí sa nevyriešený problém môže znovu ozvať. Zber údajov pokračuje.
- **Obnoviť upozornenia:** ukončí odloženie zariadenia.
- **Tiché hodiny:** používajú časové pásmo HA. Kritické zariadenie je explicitná výnimka, ale rešpektuje ručné odloženie a vypnuté notifikácie.

Opakovanie neprečítaných upozornení sa nastavuje globálne. HA udalosti pre automatizácie zostávajú oddelené od doručovania natívnych upozornení. Pri vzniku spoločného výpadku sa samostatné hlásenia nahradia skupinou.

## Pridať zariadenia

Noví kandidáti sa nachádzajú v samostatnej sekcii s počtom čakajúcich zariadení. Natívne upozornenie HA tiež informuje o čakajúcich kandidátoch. HA neposkytuje podporovaný číselný odznak pri konkrétnom vlastnom paneli.

1. Vyhľadaj a označ jedno alebo viac zariadení.
2. Skontroluj odporúčaný režim a napájanie; sieťové zariadenie nemá dostať batériový režim.
3. Voliteľne výslovne povoľ odporúčané signálové entity. Bez súhlasu zostávajú vypnuté.
4. Klikni **Skontrolovať výber**, over zdroje a potom **Začať sledovať**.
5. Skontroluj výsledok každého riadka. Ak sa zdroje od náhľadu zmenili, celý výber sa zablokuje a treba nový náhľad. Opakovanie dokončuje prerušenú operáciu bez duplikovania zariadení.

Sledované a ignorované zariadenia sa skryjú z kandidátov. Nové HA registry ID po opätovnom párovaní je nový kandidát.

## Nastavenia, história a zásoby

Globálne nastavenia zahŕňajú prah batérie, preventívny horizont, toleranciu po štarte, stabilnú obnovu, notifikácie, tiché hodiny, opakovanie a uchovávanie histórie 30–730 dní. Signál starší než 14 dní sa zhŕňa do denných priemerov. Batériové vzorky sú obmedzené osobitne pre každé zariadenie; jeden starý posledný údaj sa zachová s dátumom.

Voliteľné načítanie natívnej histórie využíva dostupný Recorder, najviac 90 dní a 600 záznamov na zdroj. Nedostupný Recorder alebo purgovaná história nevytvoria falošné merania. Podrobnosti vysvetlia, že história je prázdna, čiastočná alebo nedostupná. Bez ďalších reportov nie je možné spoľahlivo predpovedať výdrž.

**Batérie a zásoby** sú vedľajšia pomôcka v Nastaveniach: typy a počty vložených batérií, potvrdená spotreba za 90 dní, ručná zásoba a minimum. Nabíjanie sa nepočíta ako spotrebovaná batéria. Katalóg je pomocný údaj, nie podmienka sledovania.

## Jednorazový import Battery Notes

V Nastaveniach otvor **Jednorazový import a zálohy**. Najprv zobraz náhľad, exportuj zálohu, potom potvrď import. Import zachová dohľadateľné výmeny, typy a dostupnú históriu s pôvodom údajov; nepredpokladá úplný archív výmen. Skontroluj nezhodné záznamy. Battery Notes odstráň až po overení importu a následného fungovania Strážcu. Runtime používa pôvodné entity zariadení a nevyžaduje Battery Notes.

## Riešenie problémov

Pri chýbajúcich údajoch skontroluj verzie, čas posledného vyhodnotenia a detail → zdroje. Porovnaj natívny stav entity v HA; vypnutá alebo neexistujúca entita neposkytuje merania. Validný obnovený HA stav nie je dôkaz nového rádiového paketu. Ak problém trvá, prilož anonymizovanú diagnostiku a čerstvý log HA k issue. Nezverejňuj tokeny ani kompletnú konfiguráciu.

Minimálne HA entity, udalosti a akcie pre automatizácie sú popísané v [HA rozhraní](HOME_ASSISTANT.md). Detailné štatistiky zostávajú v paneli.
