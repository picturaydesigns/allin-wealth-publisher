# allin-wealth-publisher

Voll-automatische Veröffentlichung für **@allinwealth** (allin Wealth, englische Theme-Page):
**Instagram** (TikTok + YouTube Shorts als Gerüst für später), ausgelöst per **Cloud-Zeitplan**
(PC darf aus sein), **DIY pro Plattform** (eigene APIs, kein bezahlter Dienst).
1:1-Klon des erprobten `disziplin-code-publisher`.

## So funktioniert's
```
Lokal:  fertiges Reel / Karussell aus ..\allin-wealth\content
   |
   v   python stage_carousel.py --carousel N --when "..."   (oder stage_reel.py)
Cloudinary (Medien-Host)  +  Airtable "Publish-Queue-AW"
   |
   v   GitHub Actions (Cron, US-aktive Stunden)  ->  poster.py
   |        liest faellige Eintraege, postet je Plattform
   v
platforms/ig.py · youtube.py · tiktok.py  -> status/Permalink zurueck nach Airtable
```

## Dateien
- `stage_carousel.py` / `stage_reel.py` / `stage.py` — LOKAL: Medien zu Cloudinary + in die Airtable-Queue stellen.
- `poster.py` — CLOUD (GitHub Actions): fällige Einträge posten.
- `run_local.py` — Test/Notfall-Trigger lokal (`--dry` = nur anzeigen, nichts posten).
- `platforms/ig.py` — Instagram (erprobt). `youtube.py` / `tiktok.py` — Gerüst (Phase 2/3).
- `.github/workflows/publish.yml` — Cron-Runner.
- `publisher_config.example.json` — Vorlage für die lokale Konfig (echte Konfig ist gitignored).

## Wichtig (Unterschied zu disziplin-code)
- Airtable-Queue: **Publish-Queue-AW** (`tblupPQxKm9QDQSH3`, Base `app4UPxhyg94byp4X`).
- IG-Account: **@allinwealth** — Token/IDs in `..\allin-wealth\instagram_config.json`.
- **US-Publikum**: Postzeiten an US-Prime-Time ausrichten (UTC angeben! 19 Uhr US-Ost = 23:00/00:00 UTC je nach Sommerzeit).

## Start
Siehe **SETUP.md** — Schritt-für-Schritt (GitHub-Repo + Secrets + cron-job.org).
