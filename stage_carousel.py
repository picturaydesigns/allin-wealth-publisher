# -*- coding: utf-8 -*-
"""LOKAL ausfuehren (auf dem PC). Plant ein fertiges Bild-Karussell fuer die Cloud ein:
  1) laedt jede Slide zu Cloudinary hoch -> oeffentliche 4:5-JPG-URL,
  2) legt eine Zeile in der Airtable-"Publish-Queue-AW" an (image_urls, caption, Postzeit, status=scheduled).
Der Cloud-Runner (poster.py via GitHub Actions) postet sie zur Postzeit - PC kann aus sein.

Aufruf:
  python stage_carousel.py --carousel 2 --when "2026-06-13 10:00"   # Zeit in UTC! (10:00 UTC = 12:00 dt. Sommerzeit)
  python stage_carousel.py --carousel 2                              # ohne --when = sofort faellig

Konfig: publisher_config.json (Cloudinary + Airtable + Pfade). Nimmt automatisch den -v2-Ordner.
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


def cloudinary_upload(path, cc, tries=4):
    last = None
    for attempt in range(1, tries + 1):
        ts = str(int(time.time()))
        sig = hashlib.sha1(f"timestamp={ts}{cc['api_secret']}".encode("utf-8")).hexdigest()
        try:
            with open(path, "rb") as fh:
                r = requests.post(
                    f"https://api.cloudinary.com/v1_1/{cc['cloud_name']}/image/upload",
                    data={"api_key": cc["api_key"], "timestamp": ts, "signature": sig},
                    files={"file": fh}, timeout=300)
            j = r.json()
            if "public_id" in j:
                return j["public_id"]
            last = f"Antwort ohne public_id: {j}"
        except Exception as e:  # transiente Netz-/SSL-Aussetzer abfangen
            last = str(e)
        if attempt < tries:
            print(f"      (Versuch {attempt} fehlgeschlagen, neuer Versuch...)")
            time.sleep(3 * attempt)
    raise RuntimeError(f"Cloudinary-Upload fehlgeschlagen nach {tries} Versuchen: {last}")


def feed_url(public_id, cc):
    return (f"https://res.cloudinary.com/{cc['cloud_name']}/image/upload/"
            f"c_fill,ar_4:5,g_center,f_jpg,q_auto/{public_id}.jpg")


def airtable_create(at, fields):
    r = requests.post(
        f"https://api.airtable.com/v0/{at['base_id']}/{at['queue_table']}",
        headers={"Authorization": f"Bearer {at['token']}", "Content-Type": "application/json"},
        json={"fields": fields}, timeout=60)
    j = r.json()
    if "id" not in j:
        raise RuntimeError(f"Airtable-Fehler: {j}")
    return j["id"]


def find_slides(folder):
    files = sorted(f for f in os.listdir(folder) if f.lower().endswith((".png", ".jpg", ".jpeg")))
    return [os.path.join(folder, f) for f in files]


def resolve(cfg, n):
    with open(cfg["carousels_json"], encoding="utf-8-sig") as f:
        data = json.load(f)
    entry = next(c for c in data["carousels"] if c["karussell_nummer"] == n)
    base = os.path.join(cfg["content_root"], entry["ordner"].replace("/", os.sep))
    folder = base + "-v2" if os.path.isdir(base + "-v2") else base
    caption = entry.get("caption", "")
    if entry.get("hashtags"):
        caption = (caption + "\n\n" + entry["hashtags"]).strip()
    return folder, caption, entry


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--carousel", type=int, required=True)
    ap.add_argument("--when", default="", help='Postzeit UTC "YYYY-MM-DD HH:MM" (leer = sofort)')
    args = ap.parse_args()

    cfg = load_cfg()
    folder, caption, entry = resolve(cfg, args.carousel)
    slides = find_slides(folder)
    if not (2 <= len(slides) <= 10):
        raise SystemExit(f"Karussell braucht 2-10 Bilder, gefunden: {len(slides)} in {folder}")

    print(f"Karussell {args.carousel}: {entry.get('thema','')}  ({len(slides)} Slides)\nOrdner: {folder}")
    print("Lade zu Cloudinary hoch...")
    urls = []
    for s in slides:
        urls.append(feed_url(cloudinary_upload(s, cfg["cloudinary"]), cfg["cloudinary"]))
        print("   ", os.path.basename(s))

    fields = {
        "name": f"K{args.carousel} - {entry.get('thema','')}",
        "typ": "carousel",
        "image_urls": "\n".join(urls),
        "caption": caption,
        "platforms": "instagram",
        "scheduled_time": args.when,
        "status": "scheduled",
        "ki_label": bool(entry.get("ki_kennzeichnung")),
    }
    rec = airtable_create(cfg["airtable"], fields)
    print(f"\nIn Cloud-Queue gestellt (Airtable {rec}). Zeit: {args.when or 'sofort faellig'} (UTC)")


if __name__ == "__main__":
    main()
