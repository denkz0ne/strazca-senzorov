# Pravidlá dokumentácie a vydávania

Dokumentácia je súčasťou zmeny a vydania. Každý feature, oprava, migrácia alebo zmena HA rozhrania musí aktualizovať príslušný návod v tom istom pull requeste.

## Ktoré dokumenty aktualizovať

| Zmena | Povinné aktualizácie |
| --- | --- |
| Používateľská funkcionalita alebo oprava | `docs/USER_GUIDE.md`, `CHANGELOG.md` |
| Config flow, HA entity, actions, event alebo WS API | `docs/HOME_ASSISTANT.md`, `docs/DEVELOPER_GUIDE.md`; podľa potreby používateľský návod |
| Storage/model/history/import | `docs/DATA_MODEL.md`, `docs/MIGRATION.md`, testy migrácie a vývojový návod |
| Dostupnosť/diagnostika | `docs/AVAILABILITY.md`, `docs/ARCHITECTURE.md`, `OPEN_QUESTIONS.md` podľa výsledku |
| Panel UX alebo balenie | `docs/FRONTEND.md`, `docs/USER_GUIDE.md` |
| Kompatibilita alebo vydanie | ADR v `docs/decisions/`, `docs/RELEASE_CHECKLIST.md`, `README.md`, `CHANGELOG.md` |
| Každá dokončená vývojová úloha | `docs/PROGRESS.md` a plán/issue stav s overiteľnými odkazmi |

Ak dokument netreba meniť, PR musí uviesť prečo. Neoznačuj plánovanú alebo testovanú funkcionalitu ako overenú v live HA.

## Changelog a manifest verzia

Počas vývoja zapisuj používateľsky významné zmeny pod `Unreleased` v `CHANGELOG.md`. Pri verzii vytvor sekciu s presným číslom verzie, dátumom, Added/Changed/Fixed/Removed a migračnými či upgrade poznámkami. Verzia v `manifest.json`, tag, release text a changelog musia súhlasiť.

Patch verzia je pre kompatibilné opravy; minor pre kompatibilné funkcie; major pre nekompatibilnú zmenu dát alebo verejného rozhrania. Ak sa zvolí odchýlka, zdôvodni ju v PR.

## Hotfix záznam

Hotfix záznam musí byť stručný, ale reprodukovateľný: verzia/commit, symptom, dopad, presné kroky alebo pozorovaný dôkaz, koreňová príčina, oprava, regresná kontrola/CI, výsledok v cieľovom HA a rollback poznámka. Citlivé logy ani identifikátory domácnosti nevkladaj do verejných dokumentov.

## Jazyk a presnosť

- README je slovenský produktový rozcestník; vývojárske názvy a API ostávajú presne podľa kódu.
- Rozlišuj stav **navrhnuté**, **implementované**, **CI overené**, **live overené** a **vydané**.
- Pri časovo citlivých zdrojoch alebo API odkazuj na konkrétnu verziu/commit.
- Neuvádzaj, že Battery Notes je potrebná po importe; je to jednorazový zdroj.
- Nezverejňuj konkrétne používateľské entity, adresy, logy ani domáce konfigurácie.

## Kontrola pull requestu

Repo obsahuje `.github/pull_request_template.md`; autor vyplní dokumentačný audit, changelog a dôkazy. CI kontroluje kód, syntax a testy, nie správnosť prózy ani live Home Assistant správanie. Maintainer kontroluje odkazy, prechodové stavy a súlad textu so skutočným kódom.
