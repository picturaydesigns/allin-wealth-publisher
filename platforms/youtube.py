# -*- coding: utf-8 -*-
"""YouTube-Shorts-Poster (Data API v3, videos.insert).
GERUEST - wird in Phase 2 fertiggebaut + getestet (braucht Google-Cloud-Projekt + OAuth-Verifizierung).

Ablauf (geplant):
  1) OAuth-Refresh-Token -> frischer Access-Token (google-auth).
  2) Video von Cloudinary-URL nach /tmp laden (resumable upload braucht die Bytes).
  3) youtube.videos().insert(part="snippet,status", body=...) mit:
       snippet.title, snippet.description (+ "#Shorts"), snippet.tags
       status.privacyStatus = "private" (Test) / "public" (live)
       status.selfDeclaredMadeForKids = False
     Shorts = vertikales Video <= 3 Min + #Shorts -> YouTube klassifiziert automatisch.
  4) Video-ID/Permalink zurueckgeben.

WICHTIG (siehe Plan, Risiken): Fuer dauerhaft gueltige Refresh-Tokens muss die OAuth-App
verifiziert/"published" sein (sonst verfallen Test-Tokens nach 7 Tagen). Quota videos.insert
= 1600 Units (~6 Uploads/Tag bei Standard-Quota).
"""


def publish(video_url, title, description, tags, oauth, privacy="private"):
    raise NotImplementedError(
        "YouTube-Poster wird in Phase 2 gebaut (Google-Cloud-Projekt + OAuth noetig)."
    )
