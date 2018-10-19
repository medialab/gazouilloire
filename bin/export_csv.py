#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from builtins import str
import json
import sys
from datetime import datetime
try:
    from pymongo import MongoClient
except ImportError:
    from pymongo.connection import Connection as MongoClient

with open('config.json') as confile:
    conf = json.loads(confile.read())

db = MongoClient(conf['mongo']['host'], conf['mongo']['port'])[
    conf['mongo']['db']]['tweets']

print("url,user_screen_name,timestamp,user_lang,lang,coordinates,text,reply_to_url,is_retweet")
for t in db.find({}, sort=[("_id", -1)]):
    ts = datetime.strptime(
        t['created_at'], '%a %b %d %H:%M:%S +0000 %Y').isoformat()
    coords = "::".join([str(a)
                        for a in t["geo"]["coordinates"]]) if t["geo"] else ""
    text = '"' + \
        t["text"].replace('"', '""').replace("\n", " ").replace("\r", "") + '"'
    name = t.get("user_screen_name", t.get("user_name", ""))
    rt = "1" if text.startswith("RT @") else "0"
    url = t["url"] if "url" in t else "https://twitter.com/%s/status/%s" % (
        name, t["_id"])
    reply = "" if not t.get("in_reply_to_status_id_str", "") else "https://twitter.com/%s/status/%s" % (
        t.get("in_reply_to_screen_name", ""), t.get("in_reply_to_status_id_str", ""))
    print(",".join([a for a in [url, name, ts,
                                t.get("user_lang", ""), t.get("lang", ""), coords, text, reply, rt]]))
