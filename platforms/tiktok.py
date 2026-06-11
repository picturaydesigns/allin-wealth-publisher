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
import requests

from platforms.uploadpost import API, check, headers, token_ok  # noqa: F401 (token_ok re-export)


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
        files.append(("photos[]", (f"slide_{i:02d}.png", resp.content, "image/png")))
    r = requests.post(f"{API}/upload_photos", headers=headers(api_key),
                      data=data, files=files, timeout=600)
    return check(r, "tiktok", api_key)
