# -*- coding: utf-8 -*-
"""Gemeinsamer Kern fuer alle Plattformen, die ueber upload-post.com laufen (TikTok, YouTube).

Ein upload-post-"Profil" = eine Marke; daran haengen die verbundenen Social-Konten.
Auth-Header: "Authorization: Apikey <key>". Doku: https://docs.upload-post.com
"""
import requests

API = "https://api.upload-post.com/api"


def headers(api_key):
    return {"Authorization": f"Apikey {api_key}"}


def check(resp, platform):
    """Antwort pruefen und Post-ID/URL fuer das permalinks-Feld extrahieren."""
    try:
        j = resp.json()
    except ValueError:
        raise RuntimeError(f"upload-post: keine JSON-Antwort (HTTP {resp.status_code}): {resp.text[:300]}")
    if resp.status_code >= 400 or j.get("success") is False:
        raise RuntimeError(f"upload-post-Fehler (HTTP {resp.status_code}): {j}")
    results = j.get("results") or {}
    res = results.get(platform) or {}
    if isinstance(res, dict):
        if res.get("error"):
            raise RuntimeError(f"{platform}-Fehler: {res['error']}")
        ref = res.get("url") or res.get("post_id") or res.get("video_id") or res.get("publish_id")
        if ref:
            return str(ref)
    return str(j.get("request_id") or "ok")


def token_ok(api_key):
    """Read-only Gesundheits-Check: stimmt der API-Key, welche Profile haengen dran?"""
    try:
        r = requests.get(f"{API}/uploadposts/users", headers=headers(api_key), timeout=60)
        j = r.json()
        if r.status_code >= 400:
            return False, j
        return True, j.get("profiles") or j.get("users") or j
    except Exception as e:
        return False, str(e)
