# -*- coding: utf-8 -*-
"""Instagram-Poster (Instagram-Login-API, graph.instagram.com).
- publish()          : einzelnes Reel (Video)  -> Cloudinary-URL -> Container -> poll -> publish
- publish_carousel() : Bild-Karussell (2-10 Slides) -> je Slide Container -> Karussell-Container -> publish
Beide geben (media_id, permalink) zurueck. Wirft RuntimeError bei Fehler.
"""
import time
import requests

API = "https://graph.instagram.com/v22.0"


def _permalink(media_id, access_token):
    try:
        r = requests.get(f"{API}/{media_id}", params={
            "fields": "permalink", "access_token": access_token}, timeout=60).json()
        return r.get("permalink", "")
    except Exception:
        return ""


def _wait_finished(container_id, access_token, poll_max=60, poll_every=5):
    status = None
    for _ in range(poll_max):
        time.sleep(poll_every)
        s = requests.get(f"{API}/{container_id}", params={
            "fields": "status_code,status", "access_token": access_token}, timeout=60).json()
        status = s.get("status_code")
        if status == "FINISHED":
            return
        if status in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"IG Verarbeitung {status}: {s}")
    raise RuntimeError("IG Timeout: Container nicht fertig verarbeitet")


def publish(video_url, caption, ig_user_id, access_token, share_to_feed=True):
    """Postet ein Reel. Gibt (media_id, permalink) zurueck."""
    r = requests.post(f"{API}/{ig_user_id}/media", data={
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "share_to_feed": "true" if share_to_feed else "false",
        "access_token": access_token,
    }, timeout=60).json()
    if "id" not in r:
        raise RuntimeError(f"IG Container-Fehler: {r}")
    cid = r["id"]
    _wait_finished(cid, access_token)
    time.sleep(2)
    p = requests.post(f"{API}/{ig_user_id}/media_publish", data={
        "creation_id": cid, "access_token": access_token}, timeout=60).json()
    if "id" not in p:
        raise RuntimeError(f"IG Publish-Fehler: {p}")
    return p["id"], _permalink(p["id"], access_token)


def publish_carousel(image_urls, caption, ig_user_id, access_token):
    """Postet ein Bild-Karussell (2-10 Slides). Gibt (media_id, permalink) zurueck."""
    image_urls = [u.strip() for u in image_urls if u.strip()]
    if not (2 <= len(image_urls) <= 10):
        raise RuntimeError(f"Karussell braucht 2-10 Bilder, bekommen: {len(image_urls)}")

    # 1) je Slide einen carousel-item-Container
    children = []
    for url in image_urls:
        r = requests.post(f"{API}/{ig_user_id}/media", data={
            "image_url": url,
            "is_carousel_item": "true",
            "access_token": access_token,
        }, timeout=60).json()
        if "id" not in r:
            raise RuntimeError(f"IG Item-Container-Fehler: {r}")
        children.append(r["id"])

    # 2) Karussell-Container
    c = requests.post(f"{API}/{ig_user_id}/media", data={
        "media_type": "CAROUSEL",
        "children": ",".join(children),
        "caption": caption,
        "access_token": access_token,
    }, timeout=60).json()
    if "id" not in c:
        raise RuntimeError(f"IG Karussell-Container-Fehler: {c}")
    cid = c["id"]

    # 3) kurz auf FINISHED warten (Bilder meist sofort), dann veroeffentlichen
    try:
        _wait_finished(cid, access_token, poll_max=10, poll_every=3)
    except RuntimeError:
        pass  # bei Bildern oft sofort fertig -> trotzdem publizieren versuchen
    p = requests.post(f"{API}/{ig_user_id}/media_publish", data={
        "creation_id": cid, "access_token": access_token}, timeout=60).json()
    if "id" not in p:
        raise RuntimeError(f"IG Publish-Fehler: {p}")
    return p["id"], _permalink(p["id"], access_token)


def refresh_long_lived_token(access_token):
    """Verlaengert den Long-Lived-Token (alle ~60 Tage noetig)."""
    return requests.get(f"{API}/refresh_access_token", params={
        "grant_type": "ig_refresh_token", "access_token": access_token}, timeout=60).json()
