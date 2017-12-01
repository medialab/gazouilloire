#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json, sys, re
from pymongo import MongoClient
import progressbar
from gazouilloire.web.export import fields, get_field, format_csv

with open('config.json') as confile:
    conf = json.loads(confile.read())

db = MongoClient(conf['mongo']['host'], conf['mongo']['port'])[conf['mongo']['db']]['tweets']

query = {}
if len(sys.argv) == 2:
    if '{' in sys.argv[1]:
        try:
            query = eval(sys.argv[1])
        except Exception as e:
            sys.stderr.write("WARNING: query wrongly formatted: %s\n" % sys.argv[1])
            sys.exit("%s: %s\n" % (type(e), e))
    else:
        query = {"text": re.compile(sys.argv[1].replace(' ', '\s+'), re.I)}
elif len(sys.argv) > 2:
    query["$or"] = []
    for arg in sys.argv[1:]:
        query["$or"].append({"text": re.compile(arg.replace(' ', '\s+'), re.I)})

count = db.count(query)
bar = progressbar.ProgressBar(max_value=count)
print ",".join(fields)
for t in bar(db.find(query, sort=[("_id", 1)], limit=count)):
    print ",".join(format_csv(get_field(k, t)) for k in fields)

