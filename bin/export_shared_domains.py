#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json, sys
import progressbar
from collections import defaultdict
from pymongo import MongoClient
from ural import normalize_url
from gazouilloire.web.export import format_csv

with open('config.json') as confile:
    conf = json.loads(confile.read())

db = MongoClient(conf['mongo']['host'], conf['mongo']['port'])[conf['mongo']['db']]['tweets']

urls = defaultdict(int)
query = {}
#query["langs"] = "fr"

print "Counting matching results..."
count = db.count(query)
print "Querying and hashing results..."
bar = progressbar.ProgressBar(max_value=count)
for t in bar(db.find(query, limit=count, projection={"links": 1, "proper_links": 1})):
    for l in t.get("proper_links", t["links"]):
        d = normalize_url(l.split("/")[2])
        urls[d] += 1

print "Sorting and storing csv data..."
with open("shared_domains.csv", "w") as f:
    print >> f, "domain,shares"
    bar = progressbar.ProgressBar(max_value=len(urls))
    for link, shares in bar(sorted(urls.items(), key = lambda x: -x[1])):
        print >> f, '%s,%s' % (format_csv(link), shares)

