#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json, sys
import progressbar
from collections import defaultdict
from pymongo import MongoClient
from ural import normalize_url
from gazouilloire.web.export import format_csv, isodate

with open('config.json') as confile:
    conf = json.loads(confile.read())

db = MongoClient(conf['mongo']['host'], conf['mongo']['port'])[conf['mongo']['db']]['tweets']

urls = defaultdict(int)
query = {}
print "Counting matching results..."
count = db.count(query)

print "Building and storing csv data..."
with open("users_urls_domains.csv", "w") as f:
    print >> f, "user_screenname,url,normalized_url,domain,datetime,is_retweet"
    bar = progressbar.ProgressBar(max_value=count)
    for t in bar(db.find(query, limit=count, projection={"user_screen_name": 1, "links": 1, "proper_links": 1, "retweet_id": 1, "created_at": 1})):
        links = t.get("proper_links", t["links"])
        if not links:
            continue
        name = t.get("user_screen_name")
        isRT = 1 if t["retweet_id"] else 0
        dtime = isodate(t["created_at"])
        for l in links:
            lnk = normalize_url(l.replace("%0D", ""), strip_trailing_slash=True, strip_lang_subdomains=True)
            try:
                domain = normalize_url(l.split("/")[2])
            except Exception as e:
                print >> sys.stderr, "ERROR normalizing domain for url", l, type(e), e
                domain = ""
            print >> f, ",".join([format_csv(v) for v in [name, l, lnk, domain, dtime, str(isRT)]])
