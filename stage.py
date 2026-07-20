# -*- coding: utf-8 -*-
"""LOKAL ausfuehren (auf dem PC). Stellt ein fertiges Reel in die Cloud-Veroeffentlichungs-Queue:
  1) laedt die mp4 zu Cloudinary hoch (saubere URL fuer alle Plattformen),
  2) legt eine Zeile in der Airtable-Tabelle "Publish-Queue" an
     (video_url, Captions je Plattform, Kanaele, Postzeit, status=scheduled).
Der Cloud-Runner (poster.py via GitHub Actions) postet sie dann zur Postzeit - PC kann aus sein.

Aufruf:  python stage.py --reel 4 --platforms instagram,tiktok,youtube --when "2026-06-10 19:00"

Konfig (lokal, privat): publisher_config.json mit Pfaden + Cloudinary + Airtable. Siehe SETUP.md.
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


def cloudinary_upload(path, cc):
    ts = str(int(time.time()))
    sig = hashlib.sha1(f"timestamp={ts}{cc['api_secret']}".encode("utf-8")).hexdigest()
    with open(path, "rb") as fh:
        r = requests.post(
            f"https://api.cloudinary.com/v1_1/{cc['cloud_name']}/video/upload",
            data={"api_key": cc["api_key"], "timestamp": ts, "signature": sig},
            files={"file": fh}, timeout=300)
    j = r.json()
    if "secure_url" not in j:
        raise RuntimeError(f"Cloudinary-Upload fehlgeschlagen: {j}")
    return j["secure_url"]


def airtable_create(at, fields):
    """Seit 20.07.2026: Datei-Queue statt Airtable (Name bleibt, damit alle Aufrufe halten)."""
    import filequeue
    return filequeue.queue_append(fields)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reel", type=int, required=True, help="Reel-ID aus reels.json")
    ap.add_argument("--platforms", default="instagram", help="komma-getrennt: instagram,tiktok,youtube")
    ap.add_argument("--when", default="", help='Postzeit "YYYY-MM-DD HH:mm" (leer = jetzt faellig)')
    args = ap.parse_args()

    cfg = load_cfg()
    with open(cfg["reels_json"], encoding="utf-8") as f:
        reel = next(r for r in json.load(f)["reels"] if r["id"] == args.reel)

    video_path = reel["file"]
    if not os.path.isabs(video_path):
        video_path = os.path.join(cfg["content_root"], video_path)

    print(f"Lade Reel #{args.reel} ({reel['title']}) zu Cloudinary hoch...")
    url = cloudinary_upload(video_path, cfg["cloudinary"])
    print(f"Video-URL: {url}")

    # Schema EXAKT wie poster.py es liest (typ=reel -> ig.publish(video_url, caption ...)):
    fields = {
        "name": reel["title"],
        "typ": "reel",
        "video_url": url,
        "caption": reel["caption"],
        "platforms": args.platforms,
        "scheduled_time": args.when,
        "status": "scheduled",
        "ki_label": bool(reel.get("ki_required")),
    }
    rec = airtable_create(cfg["airtable"], fields)
    print(f"In Queue gestellt (Airtable {rec}). Kanaele: {args.platforms} | Zeit: {args.when or 'sofort faellig'}")


if __name__ == "__main__":
    main()
