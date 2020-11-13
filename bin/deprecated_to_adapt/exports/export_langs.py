#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json, sys
import progressbar
from collections import defaultdict
from pymongo import MongoClient
from gazouilloire.web.export import format_csv

with open('config.json') as confile:
    conf = json.loads(confile.read())

db = MongoClient(conf['mongo']['host'], conf['mongo']['port'])[conf['mongo']['db']]['tweets']

langs = defaultdict(int)
query = {}
print "Counting matching results..."
count = db.count(query)

print "Querying and hashing results..."
bar = progressbar.ProgressBar(max_value=count)
for t in bar(db.find(query, limit=count, projection={"lang": 1, "_id": 0})):
    l = t.get("lang", "")
    langs[l] += 1

print "Sorting and storing csv data..."
with open("langs.csv", "w") as f:
    print >> f, "langs,count"
    bar = progressbar.ProgressBar(max_value=len(langs))
    for l, ct in bar(sorted(langs.items(), key = lambda x: -x[1])):
        print >> f, '%s,%s' % (l, ct)
