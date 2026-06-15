# -*- coding: utf-8 -*-
"""TikTok-Poster ueber upload-post.com (auditierte TikTok-App, kein eigenes Audit noetig).

Warum nicht die offizielle TikTok Content Posting API direkt? Ohne bestandenes App-Audit
(1-4 Wochen, Demo-Video, Ausgang unsicher) postet sie nur privat (SELF_ONLY). upload-post
hat das Audit bestanden -> wir posten ueber deren REST-API sofort oeffentlich.
Eigenes Audit bleibt spaetere Spar-Option (dann diesen Adapter austauschen, Signatur behalten).

  POST {API}/upload         -> Video  (nimmt PUBLIC URL direkt an)
  POST {API}/upload_photos  -> Foto-Karussell (nur Datei-Upload -> erst herunterladen)
Kosten/Limit: Gratis-Tarif 10 Uploads/Monat, Basic unbegrenzt.
"""
from io import BytesIO

import requests

from platforms.uploadpost import API, check, headers, token_ok  # noqa: F401 (token_ok re-export)

# TikTok-Foto-Posts lehnen zu grosse Bilder mit "Unsupported image size" ab.
# Sichere Obergrenze: in eine 1080x1920-Box einpassen (Seitenverhaeltnis bleibt).
TIKTOK_MAX = (1080, 1920)


def _tiktok_safe_image(img_bytes):
    """Bild auf TikTok-vertraegliche Groesse bringen. Gibt PNG-Bytes zurueck.
    Faellt bei Problemen (kein Pillow / kaputtes Bild) auf das Original zurueck."""
    try:
        from PIL import Image
        im = Image.open(BytesIO(img_bytes))
        if im.width <= TIKTOK_MAX[0] and im.height <= TIKTOK_MAX[1]:
            return img_bytes
        im = im.convert("RGB") if im.mode not in ("RGB", "RGBA") else im
        im.thumbnail(TIKTOK_MAX, Image.LANCZOS)
        out = BytesIO()
        im.save(out, format="PNG")
        return out.getvalue()
    except Exception:
        return img_bytes


def publish_video(video_url, caption, api_key, profile, ai_generated=True):
    """Video posten. video_url = oeffentliche Cloudinary-URL (wird durchgereicht)."""
    data = {
        "user": profile,
        "platform[]": "tiktok",
        "video": video_url,
        "title": (caption or "")[:2200],
        "tiktok_title": (caption or "")[:2200],
        "post_mode": "DIRECT_POST",
        "privacy_level": "PUBLIC_TO_EVERYONE",
        "is_aigc": "true" if ai_generated else "false",
    }
    r = requests.post(f"{API}/upload", headers=headers(api_key), data=data, timeout=600)
    return check(r, "tiktok", api_key)


def publish_photos(image_urls, caption, api_key, profile, ai_generated=True):
    """Foto-Karussell posten. image_urls = Cloudinary-URLs in Slide-Reihenfolge.
    Die API verlangt Datei-Uploads -> Bilder kurz herunterladen und als multipart senden.
    ai_generated: kein is_aigc-Parameter im Foto-Endpoint -> Kennzeichnung steht im Caption-Text.
    """
    # TikTok-Foto-Titel: einzeilig, max 90 Zeichen (Umbrueche -> "post info incorrect"-Fehler)
    first_line = next((l.strip() for l in (caption or "").splitlines() if l.strip()), "")
    data = {
        "user": profile,
        "platform[]": "tiktok",
        "title": first_line[:90],
        "tiktok_description": (caption or "")[:2200],
        "post_mode": "DIRECT_POST",
        "privacy_level": "PUBLIC_TO_EVERYONE",
        "photo_cover_index": "0",
        "auto_add_music": "true",                 # TikTok verlangt Musik bei Foto-Posts
    }
    files = []
    for i, url in enumerate(image_urls, 1):
        resp = requests.get(url, timeout=120)
        resp.raise_for_status()
        img = _tiktok_safe_image(resp.content)
        files.append(("photos[]", (f"slide_{i:02d}.png", img, "image/png")))
    r = requests.post(f"{API}/upload_photos", headers=headers(api_key),
                      data=data, files=files, timeout=600)
    return check(r, "tiktok", api_key)
