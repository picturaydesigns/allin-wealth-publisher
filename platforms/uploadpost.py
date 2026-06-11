# -*- coding: utf-8 -*-
"""Gemeinsamer Kern fuer alle Plattformen, die ueber upload-post.com laufen (TikTok, YouTube).

Ein upload-post-"Profil" = eine Marke; daran haengen die verbundenen Social-Konten.
Auth-Header: "Authorization: Apikey <key>". Doku: https://docs.upload-post.com
"""
import requests

API = "https://api.upload-post.com/api"


def headers(api_key):
    return {"Authorization": f"Apikey {api_key}"}


def check(resp, platform, api_key=None):
    """Antwort pruefen und ECHTE Post-URL/-ID zurueckgeben.
    WICHTIG: 'Auftrag angenommen' (request_id) ist KEIN Erfolg - upload-post verarbeitet
    asynchron. Wir pollen den Status, bis das echte Ergebnis (success + post_url) feststeht.
    So landet nie wieder 'posted' in der Queue, wenn TikTok den Post abgewiesen hat."""
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
    rid = j.get("request_id")
    if not rid:
        raise RuntimeError(f"upload-post: weder Ergebnis noch request_id in Antwort: {str(j)[:300]}")
    if not api_key:
        raise RuntimeError(f"upload-post: async (request_id={rid}), aber kein api_key zum Status-Pollen")
    return wait_for_result(rid, platform, api_key)


def wait_for_result(request_id, platform, api_key, timeout_s=240, interval_s=10):
    """Pollt /uploadposts/status bis completed; gibt post_url zurueck oder wirft den echten Fehler."""
    import time
    waited = 0
    while True:
        r = requests.get(f"{API}/uploadposts/status", headers=headers(api_key),
                         params={"request_id": request_id}, timeout=60)
        j = r.json() if r.status_code < 500 else {}
        if j.get("status") == "completed":
            for res in j.get("results") or []:
                if res.get("platform") and res["platform"] != platform:
                    continue
                if res.get("success"):
                    return str(res.get("post_url") or res.get("platform_post_id") or "ok")
                raise RuntimeError(f"{platform}-Fehler: {res.get('error_message', 'unbekannt')[:300]}")
            raise RuntimeError(f"{platform}: Status completed, aber kein Ergebnis fuer die Plattform")
        if waited >= timeout_s:
            raise RuntimeError(f"{platform}: Verarbeitung nach {timeout_s}s nicht fertig "
                               f"(request_id={request_id}) - Status spaeter pruefen, NICHT neu posten")
        time.sleep(interval_s)
        waited += interval_s


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
