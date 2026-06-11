# SETUP — Cloud-Automatik für @allinwealth (allin Wealth)

Ziel: Beiträge gehen **aus der Cloud** raus — dein PC darf aus sein.
Kette: **cron-job.org / GitHub-Cron → GitHub Actions → poster.py → Airtable-Queue → Cloudinary → Instagram**

> Der Code ist fertig und lokal getestet. Es fehlen nur noch **deine** Schritte im Browser
> (~10 Minuten). Die geheimen Token-Werte stehen **nie** in diesem Repo — du kopierst sie
> aus den unten genannten Dateien auf deinem PC.

---

## Was schon erledigt ist (von Claude)
- Kompletter Klon des funktionierenden disziplin-code-Publishers, umgestellt auf allin Wealth.
- Airtable-Queue: **`Publish-Queue-AW`** (Basis `app4UPxhyg94byp4X`, Tabelle `tblupPQxKm9QDQSH3`).
- `publisher_config.json` (privat, gitignored) mit Cloudinary + Airtable befüllt.
- Lese-Test bestanden: Airtable-Queue erreichbar + Instagram-Token gültig.
- `git init` + erster Commit sind gemacht (Branch `master`).

## Schritt 1 — privates GitHub-Repo anlegen + hochladen
1. Gehe auf **github.com** → oben rechts **+** → **New repository**.
2. Name: **`allin-wealth-publisher`** → Haken bei **Private** setzen (wichtig!) →
   NICHTS sonst anhaken (kein README, keine .gitignore) → **Create repository**.
3. Öffne die **Eingabeaufforderung** (Windows-Taste → „cmd" tippen → Enter) und kopiere
   diese 3 Zeilen einzeln hinein (jeweils Enter):
```
cd "C:\Users\Alexa\OneDrive\Desktop\Claude\allin-wealth-publisher"
git remote add origin https://github.com/picturaydesigns/allin-wealth-publisher.git
git push -u origin master
```
   (Falls dein GitHub-Benutzername anders ist als `picturaydesigns`, ersetze ihn in der URL.)
   `publisher_config.json` wird durch `.gitignore` NICHT mit hochgeladen — gut so.
   Alternative ohne Kommandozeile: **GitHub Desktop** → *File → Add local repository* →
   Ordner wählen → *Publish repository* → Haken „Keep this code private" gesetzt lassen.

## Schritt 2 — die 5 Secrets anlegen
github.com → dein Repo `allin-wealth-publisher` → **Settings → Secrets and variables →
Actions → New repository secret**. Lege diese 5 an (Name exakt so schreiben!):

| Secret-Name | Wert | Wo der Wert herkommt |
|---|---|---|
| `AIRTABLE_BASE_ID` | `app4UPxhyg94byp4X` | steht hier (keine Geheimsache) |
| `AIRTABLE_QUEUE_TABLE` | `tblupPQxKm9QDQSH3` | steht hier (keine Geheimsache) |
| `IG_USER_ID` | `27207673485541963` | steht hier (keine Geheimsache) |
| `AIRTABLE_TOKEN` | *(geheim)* | Datei `allin-wealth\airtable_config.json` → Feld `"token"` |
| `IG_ACCESS_TOKEN` | *(geheim)* | Datei `allin-wealth\instagram_config.json` → Feld `"access_token"` |

> Die zwei geheimen Werte: Datei im Editor öffnen (Rechtsklick → Öffnen mit → Editor),
> den Wert **ohne die Anführungszeichen** kopieren und bei GitHub einfügen.

## Schritt 3 — Actions aktivieren + Erst-Test
1. Repo → Tab **Actions** → falls gefragt: **„I understand my workflows, enable them"**.
2. Links Workflow **„publish"** anklicken → rechts **Run workflow** → grüner Knopf.
3. Nach ~1 Minute auf den Lauf klicken: Im Log muss stehen **„0 faellige Eintraege."**
   (oder mehr, falls etwas in der Queue liegt). Hauptsache: **kein roter Fehler**.

## Schritt 4 — cron-job.org als zuverlässiger Wecker (US-Prime-Time)
GitHubs eigener Cron läuft schon (alle ~20 Min in US-aktiven Stunden), kann aber verspäten
und schläft nach 60 Tagen Repo-Inaktivität ein. cron-job.org stupst ihn exakt an —
genau wie beim disziplin-code-Publisher:
1. **cron-job.org** → einloggen (Konto besteht schon vom DC-Publisher) → **Cronjob erstellen**.
2. URL:
   `https://api.github.com/repos/picturaydesigns/allin-wealth-publisher/actions/workflows/publish.yml/dispatches`
3. Einstellungen → **Methode POST**, Header:
   - `Authorization` : `Bearer <dein GitHub-PAT>` *(derselbe PAT wie beim DC-Publisher-Cronjob —
     dort im bestehenden Job nachschauen/kopieren; Scope `workflow` bzw. `actions:write`)*
   - `Accept` : `application/vnd.github+json`
   - Body: `{"ref":"master"}`
4. Zeitplan (US-Prime-Time, Zeiten in UTC!): täglich z. B. **13:55, 17:55 und 23:55 UTC**
   = 9 Uhr, 13 Uhr und 19 Uhr US-Ostküste — so feuern Posts zu US-Morgen, -Mittag und
   -Prime-Time pünktlich.

---

## Posten / Einplanen (täglicher Gebrauch)
```
# Karussell N für eine Cloud-Postzeit einplanen (Zeit IMMER in UTC!):
python stage_carousel.py --carousel 3 --when "2026-06-15 23:00"

# Reel einplanen:
python stage_reel.py --file "C:\Content\allin-wealth\reels\reel_xyz.mp4" --caption "Text..." --when "2026-06-15 23:00"

# Lokal testen, was fällig wäre (postet nichts):
python run_local.py --dry
```
> **Zeitzone US-Publikum:** 19:00 New York = **23:00 UTC** (Sommer) / **00:00 UTC** (Winter).
> Beste US-Zeiten: 7–9 Uhr, 12–13 Uhr, 19–21 Uhr New-York-Zeit.

## Sicherheit
Alle Schlüssel: in privaten Configs / GitHub-Secrets — **nie** im Code, nie ins Repo. Repo ist **privat**.
Der IG-Token läuft ~60 Tage (aktuell gültig bis **10.08.2026**; erneuern via
`refresh_access_token`, dann GitHub-Secret + `allin-wealth\instagram_config.json` aktualisieren).
