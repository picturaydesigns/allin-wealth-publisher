# -*- coding: utf-8 -*-
"""CLOUD-Runner (laeuft in GitHub Actions per Cron) fuer @allinwealth (allin Wealth).
Liest die Airtable-"Publish-Queue-AW", nimmt faellige Eintraege
(status=scheduled, scheduled_time <= jetzt UTC) und postet sie auf Instagram.
Karussell: image_urls (je Zeile eine Cloudinary-URL). Reel: video_url.
Schreibt status/Permalink/Fehler zurueck. PC muss NICHT laufen.

Konfig aus Umgebungsvariablen (GitHub-Actions-Secrets) - siehe SETUP.md.
DRY_RUN=1  -> liest + zeigt faellige Eintraege, postet NICHTS (zum Testen).
"""
import datetime as dt
import os
import requests

from platforms import ig


def env(name, required=True):
    v = os.environ.get(name)
    if required and not v:
        raise SystemExit(f"Fehlende Umgebungsvariable: {name}")
    return v


AT_BASE = env("AIRTABLE_BASE_ID")
AT_TABLE = env("AIRTABLE_QUEUE_TABLE")
AT_TOKEN = env("AIRTABLE_TOKEN")
IG_USER = env("IG_USER_ID", required=False)
IG_TOKEN = env("IG_ACCESS_TOKEN", required=False)
DRY_RUN = os.environ.get("DRY_RUN", "") not in ("", "0", "false", "False")

AT_URL = f"https://api.airtable.com/v0/{AT_BASE}/{AT_TABLE}"
AT_HEADERS = {"Authorization": f"Bearer {AT_TOKEN}", "Content-Type": "application/json"}


def due_records():
    """Alle scheduled-Eintraege holen; faellige (Zeit <= jetzt UTC oder leer) zurueckgeben."""
    now = dt.datetime.utcnow()
    out, offset = [], None
    while True:
        params = {"filterByFormula": "{status}='scheduled'"}
        if offset:
            params["offset"] = offset
        j = requests.get(AT_URL, headers=AT_HEADERS, params=params, timeout=60).json()
        for rec in j.get("records", []):
            when = (rec.get("fields", {}).get("scheduled_time") or "").strip()
            due = True
            if when:
                try:
                    due = dt.datetime.strptime(when, "%Y-%m-%d %H:%M") <= now
                except ValueError:
                    due = True
            if due:
                out.append(rec)
        offset = j.get("offset")
        if not offset:
            break
    return out


def update(rec_id, fields):
    requests.patch(f"{AT_URL}/{rec_id}", headers=AT_HEADERS, json={"fields": fields}, timeout=60)


def post_one(rec):
    f = rec["fields"]
    name = f.get("name", "?")
    typ = (f.get("typ") or "carousel").strip()
    platforms = [p.strip() for p in (f.get("platforms") or "instagram").split(",") if p.strip()]
    results, errors = {}, {}

    for p in platforms:
        try:
            if p == "instagram":
                if typ == "carousel":
                    urls = [u for u in (f.get("image_urls") or "").splitlines() if u.strip()]
                    mid, link = ig.publish_carousel(urls, f.get("caption", ""), IG_USER, IG_TOKEN)
                else:  # reel
                    mid, link = ig.publish(f["video_url"], f.get("caption", ""), IG_USER, IG_TOKEN)
                results["instagram"] = link or mid
            else:
                errors[p] = "Plattform noch nicht angebunden"
        except Exception as e:  # eine Plattform darf die anderen nicht blockieren
            errors[p] = str(e)

    fields = {
        "status": "posted" if results and not errors else ("failed" if errors and not results else "partial"),
        "permalinks": "; ".join(f"{k}:{v}" for k, v in results.items()),
        "last_error": "; ".join(f"{k}:{v}" for k, v in errors.items()),
        "posted_at": dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
    }
    update(rec["id"], fields)
    print(f"[{name}] typ={typ} -> ok={list(results)} fehler={list(errors)}")


def main():
    recs = due_records()
    print(f"{len(recs)} faellige Eintraege." + (" (DRY_RUN: poste nichts)" if DRY_RUN else ""))
    for rec in recs:
        f = rec["fields"]
        if DRY_RUN:
            n_imgs = len([u for u in (f.get("image_urls") or "").splitlines() if u.strip()])
            print(f"  WUERDE POSTEN: [{f.get('name','?')}] typ={f.get('typ')} "
                  f"slides={n_imgs} zeit={f.get('scheduled_time') or 'sofort'}")
        else:
            post_one(rec)


if __name__ == "__main__":
    main()
