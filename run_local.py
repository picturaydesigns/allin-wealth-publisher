# -*- coding: utf-8 -*-
"""Loest poster.py LOKAL aus (Test / Notfall-Trigger, falls GitHubs Cron versagt).
Liest die Secrets aus den Configs, setzt sie als Env-Variablen, ruft poster.main().
Aufruf:  python run_local.py            (postet faellige Eintraege)
         python run_local.py --dry      (zeigt nur, was faellig waere - postet nichts)
"""
import json, os, sys

PUB = os.path.dirname(os.path.abspath(__file__))
AW = r"C:\Users\Alexa\OneDrive\Desktop\Claude\allin-wealth"

ig = json.load(open(os.path.join(AW, "instagram_config.json"), encoding="utf-8-sig"))
cfg = json.load(open(os.path.join(PUB, "publisher_config.json"), encoding="utf-8-sig"))
at = cfg["airtable"]

os.environ["AIRTABLE_BASE_ID"]     = at["base_id"]
os.environ["AIRTABLE_QUEUE_TABLE"] = at["queue_table"]
os.environ["AIRTABLE_TOKEN"]       = at["token"]
os.environ["IG_USER_ID"]           = ig["instagram_user_id"]
os.environ["IG_ACCESS_TOKEN"]      = ig["access_token"]
if "--dry" in sys.argv:
    os.environ["DRY_RUN"] = "1"


# upload-post (TikTok + YouTube) aus der Publisher-Config
HERE = os.path.dirname(os.path.abspath(__file__))
up = json.load(open(os.path.join(HERE, "publisher_config.json"), encoding="utf-8")).get("uploadpost", {})
if up:
    os.environ["UPLOADPOST_API_KEY"] = up["api_key"]
    os.environ["UPLOADPOST_PROFILE"] = up["profile"]

import poster  # liest die Env-Variablen beim Import
poster.main()
