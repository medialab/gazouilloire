#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json, sys
import progressbar
from pymongo import MongoClient
from gazouilloire.web.export import format_csv

with open('config.json') as confile:
    conf = json.loads(confile.read())

db = MongoClient(conf['mongo']['host'], conf['mongo']['port'])[conf['mongo']['db']]['tweets']

accents = {
    u"á": "a",
    u"à": "a",
    u"â": "a",
    u"é": "e",
    u"è": "e",
    u"ê": "e",
    u"ë": "e",
    u"ç": "c",
    u"î": "i",
    u"ï": "i",
    u"ô": "o",
    u"ö": "o",
    u"ù": "u",
    u"Û": "u",
    u"ü": "u"
};

hashtags = {}
query = {}
#query["langs"] = "fr"
print "Counting matching results..."
count = db.count(query)

print "Querying and hashing results..."
bar = progressbar.ProgressBar(max_value=count)
for t in bar(db.find(query, limit=count, projection={"hashtags": 1, "_id": 0})):
    for h in t.get("hashtags", []):
        h = h.lower()
        for acc, noa in accents.items():
            h = h.replace(acc, noa)
        if h not in hashtags:
            hashtags[h] = 0
        hashtags[h] += 1

print "Sorting and storing csv data..."
with open("hashtags.csv", "w") as f:
    print >> f, "hashtags,count"
    bar = progressbar.ProgressBar(max_value=len(hashtags))
    for h, ct in bar(sorted(hashtags.items(), key = lambda x: -x[1])):
        print >> f, '%s,%s' % (format_csv(h), ct)
