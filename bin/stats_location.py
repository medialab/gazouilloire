#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
import json
import sys
import progressbar
from collections import defaultdict
try:
    from pymongo import MongoClient
except ImportError:
    from pymongo.connection import Connection as MongoClient

with open('config.json') as confile:
    conf = json.loads(confile.read())

db = MongoClient(conf['mongo']['host'], conf['mongo']['port'])[
    conf['mongo']['db']]['tweets']

locations = defaultdict(int)

query = {}
count = db.count(query)
bar = progressbar.ProgressBar(max_value=count)
for t in bar(db.find(query, limit=count, projection={"user_location": 1})):
    locations[t.get("user_location") or ""] += 1

print("location,count")
for loc in sorted(locations, key=locations.get, reverse=True):
    print('"%s",%s' % (loc.replace('"', '""'), locations[loc]))
