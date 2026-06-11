# -*- coding: utf-8 -*-
"""YouTube-Shorts-Poster ueber upload-post.com (gleicher API-Key wie TikTok).

Warum nicht die YouTube Data API direkt? Die braeuchte ein Google-Cloud-Projekt, einen
OAuth-Verifizierungsprozess und hat enge Upload-Quoten (~6/Tag). upload-post uebernimmt
das alles; das YouTube-Konto wird einfach im upload-post-Profil der Marke verbunden.

  POST {API}/upload  -> Video (nimmt PUBLIC URL direkt an); 9:16 unter 3 Min = Short.
KI-Kennzeichnung: containsSyntheticMedia=true (offizielle YouTube-Deklaration).
"""
import requests

from platforms.uploadpost import API, check, headers


def publish(video_url, title, description, api_key, profile, ai_generated=True, tags=None,
            lang="de", audio_lang="de-DE"):
    """Short posten. video_url = oeffentliche Cloudinary-URL (wird durchgereicht).
    lang/audio_lang: BCP-47 (englische Marken: lang="en", audio_lang="en-US")."""
    data = {
        "user": profile,
        "platform[]": "youtube",
        "video": video_url,
        "title": (title or "")[:100],             # YouTube-Titel max 100 Zeichen
        "youtube_title": (title or "")[:100],
        "youtube_description": (description or "")[:5000],
        "selfDeclaredMadeForKids": "false",
        "containsSyntheticMedia": "true" if ai_generated else "false",
        "defaultLanguage": lang,
        "defaultAudioLanguage": audio_lang,
    }
    if tags:
        data["tags[]"] = tags
    r = requests.post(f"{API}/upload", headers=headers(api_key), data=data, timeout=600)
    return check(r, "youtube")
