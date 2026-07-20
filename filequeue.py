# -*- coding: utf-8 -*-
"""Datei-basierte Publish-Queue (ersetzt Airtable seit 20.07.2026 - Gratis-API-Limit).
queue.json liegt im Repo: Stager haengen Eintraege an (git push), poster.py in GitHub
Actions liest faellige Eintraege und committet Statusaenderungen zurueck. Zeiten in UTC."""
import datetime as dt
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def _pfad():
    return os.environ.get("QUEUE_FILE") or os.path.join(HERE, "queue.json")


def lade():
    p = _pfad()
    if not os.path.exists(p):
        return {"entries": []}
    with open(p, encoding="utf-8-sig") as f:
        return json.load(f)


def speichere(daten):
    tmp = _pfad() + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(daten, f, ensure_ascii=False, indent=1)
    os.replace(tmp, _pfad())


def neue_id(name):
    stamp = dt.datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    kurz = re.sub(r"[^A-Za-z0-9_-]", "_", (name or "x"))[:40]
    return "q-%s-%s" % (stamp, kurz)


import re  # noqa: E402  (fuer neue_id)


def queue_append(fields):
    """Eintrag anhaengen + zu GitHub pushen (pull --rebase mit Autostash, 3 Versuche)."""
    import subprocess

    def git(*args, muss=True):
        r = subprocess.run(["git", "-c", "rebase.autostash=true"] + list(args),
                           cwd=HERE, capture_output=True, text=True)
        if muss and r.returncode != 0:
            raise RuntimeError("git %s: %s" % (args[0], (r.stderr or r.stdout or "?")[-220:]))
        return r

    git("pull", "--rebase", muss=False)
    daten = lade()
    eintrag = dict(fields)
    # Alt-Feldname vereinheitlichen (Stager schrieben ki_label, Poster liest ai_label)
    if "ki_label" in eintrag and "ai_label" not in eintrag:
        eintrag["ai_label"] = bool(eintrag.pop("ki_label"))
    eintrag.setdefault("status", "scheduled")
    eintrag["id"] = neue_id(eintrag.get("name"))
    daten.setdefault("entries", []).append(eintrag)
    speichere(daten)
    git("add", "queue.json")
    git("commit", "-m", "queue: +%s" % eintrag.get("name", "?"), muss=False)
    p = None
    for _ in range(3):
        p = git("push", muss=False)
        if p.returncode == 0:
            return eintrag["id"]
        git("pull", "--rebase", muss=False)
    raise RuntimeError("git push fehlgeschlagen: " + ((p.stderr if p else "") or "?")[-220:])
