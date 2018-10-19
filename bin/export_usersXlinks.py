#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
import json
import sys
import progressbar
try:
    from pymongo import MongoClient
except ImportError:
    from pymongo.connection import Connection as MongoClient

with open('config.json') as confile:
    conf = json.loads(confile.read())

db = MongoClient(conf['mongo']['host'], conf['mongo']['port'])[
    conf['mongo']['db']]['tweets']

print("user_screenname,links,is_retweet")
query = {"langs": "fr"}
count = db.count(query)

bar = progressbar.ProgressBar(max_value=count)
for t in bar(db.find(query, limit=count, projection={"user_screen_name": 1, "links": 1, "proper_links": 1, "retweet_id": 1})):
    name = t.get("user_screen_name")
    links = t.get("proper_links", t["links"])
    isRT = 1 if t["retweet_id"] else 0
    if not links:
        continue
    print('%s,"%s",%s' % (name, "|".join(links), isRT))
