# -*- coding: utf-8 -*-
"""LOKAL ausfuehren. Plant ein fertiges Reel (Video) fuer die Cloud ein:
  1) laedt die mp4 zu Cloudinary hoch (oeffentliche URL),
  2) legt eine Zeile in der Airtable-"Publish-Queue-AW" an (typ=reel, video_url, caption, Postzeit).
Der Cloud-Runner (poster.py via GitHub Actions) postet sie zur Postzeit als Instagram-Reel - PC aus ok.

Aufruf:
  python stage_reel.py --file "C:\\Content\\allin-wealth\\reels\\reel_xyz.mp4" --caption "Text..." --when "2026-06-15 06:00"
  python stage_reel.py --file "...mp4" --caption "..."                 # ohne --when = sofort faellig
  Optional: --name "Kurzname"  --ki   (--ki setzt das KI-Label-Flag)

Zeit IMMER in UTC! (dt. Sommerzeit = UTC+2 -> 19:00 dt. = 17:00 UTC)
Konfig: publisher_config.json (Cloudinary + Airtable).
"""
import argparse
import hashlib
import json
import os
import time
import requests

HERE = os.path.dirname(os.path.abspath(__file__))


def load_cfg():
    with open(os.path.join(HERE, "publisher_config.json"), encoding="utf-8") as f:
        return json.load(f)


def cloudinary_video_upload(path, cc, tries=4):
    last = None
    for attempt in range(1, tries + 1):
        ts = str(int(time.time()))
        sig = hashlib.sha1(f"timestamp={ts}{cc['api_secret']}".encode("utf-8")).hexdigest()
        try:
            with open(path, "rb") as fh:
                r = requests.post(
                    f"https://api.cloudinary.com/v1_1/{cc['cloud_name']}/video/upload",
                    data={"api_key": cc["api_key"], "timestamp": ts, "signature": sig},
                    files={"file": fh}, timeout=600)
            j = r.json()
            if "secure_url" in j:
                return j["secure_url"]
            last = f"Antwort ohne secure_url: {j}"
        except Exception as e:
            last = str(e)
        if attempt < tries:
            print(f"   (Versuch {attempt} fehlgeschlagen, neuer Versuch...)")
            time.sleep(3 * attempt)
    raise RuntimeError(f"Cloudinary-Upload fehlgeschlagen nach {tries} Versuchen: {last}")


def airtable_create(at, fields):
    r = requests.post(
        f"https://api.airtable.com/v0/{at['base_id']}/{at['queue_table']}",
        headers={"Authorization": f"Bearer {at['token']}", "Content-Type": "application/json"},
        json={"fields": fields}, timeout=60)
    j = r.json()
    if "id" not in j:
        raise RuntimeError(f"Airtable-Fehler: {j}")
    return j["id"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", help="Pfad zur fertigen mp4 (oder --reel verwenden)")
    ap.add_argument("--reel", type=int, help="Reel-ID aus reels.json (zieht Datei+Caption automatisch)")
    ap.add_argument("--caption", default="")
    ap.add_argument("--when", default="", help='Postzeit UTC "YYYY-MM-DD HH:MM" (leer = sofort)')
    ap.add_argument("--name", default="")
    ap.add_argument("--ki", action="store_true", help="KI-Label-Flag setzen")
    args = ap.parse_args()

    cfg = load_cfg()
    file, caption, name, ki = args.file, args.caption, args.name, args.ki

    if args.reel is not None:
        with open(cfg["reels_json"], encoding="utf-8-sig") as f:
            entry = next(r for r in json.load(f)["reels"] if r["id"] == args.reel)
        file = entry["file"]
        caption = entry.get("caption", "")
        name = entry.get("title", f"reel-{args.reel}")
        ki = bool(entry.get("ki_required"))
        print(f"Reel #{args.reel} aus reels.json: {name}")

    if not file or not os.path.isfile(file):
        raise SystemExit(f"Datei nicht gefunden: {file}")
    name = name or os.path.splitext(os.path.basename(file))[0]

    print(f"Reel: {name}\nLade zu Cloudinary hoch (kann bei groesseren Videos dauern)...")
    url = cloudinary_video_upload(file, cfg["cloudinary"])
    print(f"Video-URL: {url}")

    fields = {
        "name": name,
        "typ": "reel",
        "video_url": url,
        "caption": caption,
        "platforms": "instagram",
        "scheduled_time": args.when,
        "status": "scheduled",
        "ki_label": bool(ki),
    }
    rec = airtable_create(cfg["airtable"], fields)
    print(f"\nIn Cloud-Queue gestellt (Airtable {rec}). Zeit: {args.when or 'sofort faellig'} (UTC)")


if __name__ == "__main__":
    main()
