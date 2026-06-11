# -*- coding: utf-8 -*-
"""TikTok-Poster (Content Posting API).
GERUEST - wird in Phase 3 fertiggebaut + getestet (braucht Developer-App + Audit-Freigabe).

Ablauf (geplant, FILE_UPLOAD - NICHT PULL_FROM_URL):
  PULL_FROM_URL verlangt Verifizierung der Host-Domain; die haben wir bei res.cloudinary.com
  nicht -> daher Bytes selbst hochladen.
  1) OAuth-Refresh-Token -> frischer Access-Token (Scope video.publish).
  2) Video von Cloudinary-URL nach /tmp laden; Dateigroesse bestimmen.
  3) POST /v2/post/publish/video/init/ mit source_info(source=FILE_UPLOAD, video_size,
     chunk_size, total_chunk_count) + post_info(title/caption, privacy_level,
     disable_comment, ...). Optional AIGC-Label: brand_content_toggle / "AI-generated"-Flag.
  4) Bytes an die zurueckgegebene upload_url chunked senden.
  5) Status pollen (/v2/post/publish/status/fetch/) bis PUBLISH_COMPLETE.
  6) Publish-ID/Permalink zurueckgeben.

WICHTIG (siehe Plan, Risiken): Vor TikTok-App-Audit ist privacy_level auf SELF_ONLY/privat
beschraenkt -> erst privat testen, oeffentlich erst nach Freigabe.
"""


def publish(video_url, caption, oauth, privacy="SELF_ONLY", ai_generated=True):
    raise NotImplementedError(
        "TikTok-Poster wird in Phase 3 gebaut (Developer-App + Audit-Freigabe noetig)."
    )
