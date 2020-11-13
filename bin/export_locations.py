#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
import json
import sys
import progressbar
from collections import defaultdict
from gazouilloire.database.mongomanager import MongoManager

with open('config.json') as confile:
    conf = json.loads(confile.read())

db = MongoManager(conf['database']['host'], conf['database']['port'], conf['database']['db']).tweets

locations = defaultdict(int)

query = {}
count = db.count(query)
bar = progressbar.ProgressBar(max_value=count)
for t in bar(db.find(query, limit=count, projection={"user_location": 1})):
    locations[t.get("user_location") or ""] += 1

print("location,count")
for loc in sorted(locations, key=locations.get, reverse=True):
    print('"%s",%s' % (loc.replace('"', '""'), locations[loc]))
