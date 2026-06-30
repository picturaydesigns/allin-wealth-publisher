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


MAX_PER_RUN = int(os.environ.get("MAX_PER_RUN", "1"))   # Anti-Blast: hoechstens N Posts pro Lauf


def parse_when(when):
    s = (when or "").strip().replace("T", " ").replace("Z", "").split(".")[0]
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return dt.datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def posted_content_keys(days=10):
    """Inhalte (video_url/image_urls), die in den letzten <days> Tagen schon gepostet wurden -> Anti-Duplikat."""
    cutoff = (dt.datetime.utcnow() - dt.timedelta(days=days)).strftime("%Y-%m-%d %H:%M")
    keys, offset = set(), None
    while True:
        params = [("filterByFormula", "{status}='posted'"),
                  ("fields[]", "video_url"), ("fields[]", "image_urls"),
                  ("fields[]", "name"), ("fields[]", "posted_at")]
        if offset:
            params.append(("offset", offset))
        j = requests.get(AT_URL, headers=AT_HEADERS, params=params, timeout=60).json()
        for rec in j.get("records", []):
            f = rec.get("fields", {})
            if (f.get("posted_at") or "") < cutoff:
                continue
            k = (f.get("video_url") or f.get("image_urls") or f.get("name") or "").strip()
            if k:
                keys.add(k)
        offset = j.get("offset")
        if not offset:
            break
    return keys


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
            if not when:
                out.append(rec)            # leeres Feld = sofort faellig
                continue
            t = parse_when(when)
            if t is None:
                print(f"  WARN: unlesbares scheduled_time '{when}' -> uebersprungen (postet NICHT)")
                continue
            if t <= now:
                out.append(rec)
        offset = j.get("offset")
        if not offset:
            break
    return out


def update(rec_id, fields):
    """Status zurueckschreiben — MIT Erfolgspruefung + Retry. Stilles Fehlschlagen wuerde den
    Eintrag 'scheduled' lassen -> naechster Lauf postet erneut (Mehrfach-Post-Ursache)."""
    last = None
    payload = dict(fields)
    for attempt in range(1, 4):
        r = requests.patch(f"{AT_URL}/{rec_id}", headers=AT_HEADERS, json={"fields": payload}, timeout=60)
        if r.status_code == 200:
            return True
        last = f"HTTP {r.status_code}: {r.text[:160]}"
        if r.status_code == 422 and "MULTIPLE_CHOICE" in r.text and payload.get("status") not in (None, "posted"):
            payload = dict(payload); payload["status"] = "posted"
            print("  Status-Option ungueltig -> Fallback status=posted")
            continue
        print(f"  WARN: Airtable-Update Versuch {attempt}/3 fehlgeschlagen -> {last}")
    print(f"  FEHLER: Status NICHT geschrieben ({last}) — Eintrag {rec_id} bleibt scheduled!")
    return False


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
                yt_title = (f.get("yt_title") or f.get("name")
                            or next((l.strip() for l in (f.get("caption") or "").splitlines() if l.strip()), "")
                            or "Video")[:100]
                results["youtube"] = youtube.publish(f["video_url"], yt_title,
                                                     f.get("yt_description") or f.get("caption", "") or yt_title,
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
    posted_keys = posted_content_keys()      # Anti-Duplikat (letzte 10 Tage)
    AUTHORS = {"confucius", "konfuzius", "benjamin franklin", "marcus aurelius", "epictetus",
               "epiktet", "lao tzu", "laozi", "seneca", "socrates", "sokrates", "plato", "platon",
               "aristotle", "aristoteles", "mark twain", "buddha", "rumi", "nietzsche", "goethe"}

    def is_junk(f):
        return (f.get("name") or "").strip().lower() in AUTHORS

    def ckey(f):
        return (f.get("video_url") or f.get("image_urls") or f.get("name") or "").strip()

    eligible = []
    for rec in recs:
        f = rec["fields"]
        if is_junk(f):
            print(f"  UEBERSPRUNGEN (Muell-Kachel): {f.get('name')}")
            if not DRY_RUN:
                update(rec["id"], {"status": "skipped", "last_error": "Autoren-/Muell-Kachel"})
            continue
        if ckey(f) and ckey(f) in posted_keys:
            print(f"  UEBERSPRUNGEN (Duplikat): {f.get('name')}")
            if not DRY_RUN:
                update(rec["id"], {"status": "skipped", "last_error": "Duplikat (<10 Tage schon gepostet)"})
            continue
        eligible.append(rec)

    eligible.sort(key=lambda r: r["fields"].get("scheduled_time") or "")   # aeltester zuerst
    batch = eligible[:MAX_PER_RUN]
    print(f"{len(recs)} faellig | {len(eligible)} nach Filter | poste {len(batch)} (Cap {MAX_PER_RUN})"
          + (" (DRY_RUN: poste nichts)" if DRY_RUN else ""))
    for rec in batch:
        f = rec["fields"]
        if DRY_RUN:
            print(f"  WUERDE POSTEN: [{f.get('name','?')}] zeit={f.get('scheduled_time') or 'sofort'}")
        else:
            post_one(rec)


if __name__ == "__main__":
    main()
