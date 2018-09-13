#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os, sys, re
import csv, json
from pymongo import MongoClient
from gazouilloire.web.export import yield_csv, get_thread_ids_from_ids

with open('config.json') as confile:
    conf = json.loads(confile.read())

db = MongoClient(conf['mongo']['host'], conf['mongo']['port'])[conf['mongo']['db']]['tweets']

verbose = True
if len(sys.argv) > 1 and "--quiet" in sys.argv:
    sys.argv.remove("--quiet")
    verbose = False

query = {}
if len(sys.argv) == 2:
    if '{' in sys.argv[1]:
        try:
            query = eval(sys.argv[1])
        except Exception as e:
            sys.stderr.write("WARNING: query wrongly formatted: %s\n" % sys.argv[1])
            sys.exit("%s: %s\n" % (type(e), e))
    elif os.path.exists(sys.argv[1]):
          with open(sys.argv[1]) as f:
              ids = sorted([t.get("id", t.get("_id")) for t in csv.DictReader(f)])
          ids = get_thread_ids_from_ids(ids, db)
          query = {"_id": {"$in": ids}}
    else:
        query = {"text": re.compile(sys.argv[1].replace(' ', '\s+'), re.I)}
elif len(sys.argv) > 2:
    query["$or"] = []
    for arg in sys.argv[1:]:
        query["$or"].append({"text": re.compile(arg.replace(' ', '\s+'), re.I)})

extra_fields = conf.get('export', {}).get('extra_fields', [])
count = db.count(query)
iterator = yield_csv(db.find(query, sort=[("_id", 1)], limit=count), extra_fields=extra_fields)
if verbose:
    import progressbar
    bar = progressbar.ProgressBar(max_value=count)
    iterator = bar(iterator)
for t in iterator:
    print t
