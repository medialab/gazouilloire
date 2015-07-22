#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json, sys
from datetime import datetime
from pymongo import MongoClient
from config import MONGO_DATABASE

db = MongoClient("localhost", 27017)[MONGO_DATABASE]['tweets']

print "url,user_screen_name,timestamp,lang,coordinates,retweets,favorites,text"
for t in db.find(sort=[("_id", -1)]):
    ts = datetime.strptime(t['created_at'], '%a %b %d %H:%M:%S +0000 %Y').isoformat()
    coords = "::".join([str(a) for a in t["geo"]["coordinates"]]) if t["geo"] else ""
    text = '"' + t["text"].replace('"', '""').replace("\n", " ").replace("\r", "") + '"'
    name = t.get("user_screen_name", t.get("user_name", ""))
    url = t["url"] if "url" in t else "https://twitter.com/%s/status/%s" % (name, t["_id"])
    print ",".join([a.encode("utf-8") for a in [url, name, ts, t["lang"], coords, str(t['retweet_count']), str(t['favorite_count']), text]])

