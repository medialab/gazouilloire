#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys, json, csv
import progressbar
from gazouilloire.database.mongomanager import MongoManager

try:
    with open(sys.argv[1]) as csvfile:
        data = list(csv.DictReader(csvfile))
        assert("id" in data[0] and data[0]["id"])
except Exception as e:
    print "Cannot load CSV file with id field %s" % " ".join(sys.argv[1:])
    print "%s: %s" % (type(e), e)
    exit(1)


with open('config.json') as confile:
    conf = json.loads(confile.read())
SELECTED_FIELD = conf.get("export", {}).get("selected_field")
if not SELECTED_FIELD:
    print "Please setup a selected_field in the config first"
    exit(1)


db = MongoManager(conf['database']['host'], conf['database']['port'], conf['database']['db']).tweets
db.create_index(SELECTED_FIELD)

bar = progressbar.ProgressBar(max_value=len(data) - 1)
for tweet in bar(data):
    res = db.update_one({"_id": tweet["id"]}, {"$set": {SELECTED_FIELD: True}}, upsert=False)

