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
UP_KEY = env("UPLOADPOST_API_KEY", required=False)      # upload-post.com (TikTok + YouTube)
UP_PROFILE = env("UPLOADPOST_PROFILE", required=False)  # Profilname dort (= Marke)
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
            elif p == "tiktok":
                from platforms import tiktok
                if not (UP_KEY and UP_PROFILE):
                    raise RuntimeError("UPLOADPOST_API_KEY / UPLOADPOST_PROFILE nicht gesetzt")
                cap = f.get("caption_tiktok") or f.get("caption", "")
                ai = bool(f.get("ai_label", True))
                if typ == "carousel":
                    urls = [u for u in (f.get("image_urls") or "").splitlines() if u.strip()]
                    results["tiktok"] = tiktok.publish_photos(urls, cap, UP_KEY, UP_PROFILE, ai_generated=ai)
                else:
                    results["tiktok"] = tiktok.publish_video(f["video_url"], cap, UP_KEY, UP_PROFILE, ai_generated=ai)
            elif p == "youtube":
                from platforms import youtube
                if not (UP_KEY and UP_PROFILE):
                    raise RuntimeError("UPLOADPOST_API_KEY / UPLOADPOST_PROFILE nicht gesetzt")
                results["youtube"] = youtube.publish(f["video_url"], f.get("yt_title") or f.get("name", ""),
                                                     f.get("yt_description") or f.get("caption", ""),
                                                     UP_KEY, UP_PROFILE, ai_generated=bool(f.get("ai_label", True)), lang="en", audio_lang="en-US")
            else:
                errors[p] = "Plattform noch nicht angebunden"
        except Exception as e:  # eine Plattform darf die anderen nicht blockieren
            errors[p] = str(e)

    # Voruebergehende Drosselungen (z.B. TikTok-Tageskontingent der upload-post-App):
    # Eintrag bleibt "scheduled" -> der naechste Cron-Lauf (~20 Min) versucht es erneut.
    TRANSIENT = ("temporary restriction", "user cap", "try again in a few hours", "rate limit")
    all_transient = errors and not results and all(
        any(t in msg.lower() for t in TRANSIENT) for msg in errors.values())
    if all_transient:
        update(rec["id"], {"last_error": "RETRY " + "; ".join(f"{k}:{v}" for k, v in errors.items())[:500]})
        print(f"[{name}] voruebergehend gedrosselt, bleibt scheduled (Retry naechster Lauf)")
        return

    fields = {
        "status": "posted" if results and not errors else ("failed" if errors and not results else "partial"),
        "permalinks": "; ".join(f"{k}:{v}" for k, v in results.items()),
        "last_error": "; ".join(f"{k}:{v}" for k, v in errors.items()),
        "posted_at": dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
    }
    update(rec["id"], fields)
    print(f"[{name}] typ={typ} -> ok={list(results)} fehler={list(errors)}")


def main():
    # IG-TOKEN-CHECK (read-only) - macht stille Token-Ausfaelle sichtbar (wie EG)
    if IG_USER and IG_TOKEN:
        ok, info = ig.token_ok(IG_USER, IG_TOKEN)
        if ok:
            print(f"IG-TOKEN OK -> @{info.get('username')} ({info.get('followers_count')} Follower)")
        else:
            print(f"IG-TOKEN TOT -> {info}  -> neuen Token holen + Secret IG_ACCESS_TOKEN aktualisieren.")
    if UP_KEY:
        from platforms import uploadpost
        ok, info = uploadpost.token_ok(UP_KEY)
        print(f"UPLOAD-POST {'OK' if ok else 'TOT'} -> {str(info)[:100]}")
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
