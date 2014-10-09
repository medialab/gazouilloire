#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json, sys
from datetime import datetime
from pymongo import MongoClient

with open('config.json') as confile:
    conf = json.loads(confile.read())

db = MongoClient(conf['mongo']['host'], conf['mongo']['port'])[conf['mongo']['db']]['tweets']

print "url,user_screen_name,text,timestamp,lang,coordinates"
for t in db.find(sort=[("_id", -1)]):
    ts = datetime.strptime(t['created_at'], '%a %b %d %H:%M:%S +0000 %Y').isoformat()
    coords = "::".join([str(a) for a in t["geo"]["coordinates"]]) if t["geo"] else ""
    text = '"' + t["text"].replace('"', '""') + '"'
    name = t.get("user_screen_name", t.get("user_name", ""))
    print ",".join([a.encode("utf-8") for a in [t["url"],name,text,ts,t["lang"],coords]])

