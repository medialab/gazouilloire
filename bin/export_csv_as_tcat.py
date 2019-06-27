#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os, sys, re
import csv, json
from pymongo import MongoClient
from gazouilloire.web.export import yield_csv, get_thread_ids_from_ids

try:
    with open(os.path.join(os.path.dirname(__file__), '..', 'config.json')) as confile:
         conf = json.loads(confile.read())
except Exception as e:
    sys.stderr.write("ERROR: Impossible to read config.json: %s %s" % (type(e), e))
    exit(1)
THREADS = conf.get('grab_conversations', False)
SELECTED_FIELD = conf.get('export', {}).get('selected_field', None)
EXTRA_FIELDS = conf.get('export', {}).get('extra_fields', [])

try:
    mongodb = MongoClient(conf['mongo']['host'], conf['mongo']['port'])[conf['mongo']['db']]['tweets']
except Exception as e:
    sys.stderr.write("ERROR: Could not initiate connection to MongoDB: %s %s" % (type(e), e))
    exit(1)

verbose = True
if len(sys.argv) > 1 and "--quiet" in sys.argv:
    sys.argv.remove("--quiet")
    verbose = False

only_selected = False
if SELECTED_FIELD and len(sys.argv) > 1 and "--selected" in sys.argv:
    sys.argv.remove("--selected")
    only_selected = True

include_threads = True
if THREADS and len(sys.argv) > 1 and "--no-threads" in sys.argv:
    sys.argv.remove("--no-threads")
    include_threads = False

limit = 0
if len(sys.argv) > 2 and "--limit" in sys.argv:
    limit = sys.argv[sys.argv.index('--limit') + 1]
    sys.argv.remove("--limit")
    sys.argv.remove(limit)
    limit = int(limit)

query = {}
if only_selected:
    query = {SELECTED_FIELD: True}
if len(sys.argv) == 2:
    if '{' in sys.argv[1]:
        try:
            query = eval(sys.argv[1])
            if only_selected:
                query = {"$and": [query, {SELECTED_FIELD: True}]}
        except Exception as e:
            sys.stderr.write("WARNING: query wrongly formatted: %s\n" % sys.argv[1])
            sys.exit("%s: %s\n" % (type(e), e))
    elif os.path.exists(sys.argv[1]):
        with open(sys.argv[1]) as f:
            ids = sorted([t.get("id", t.get("_id")) for t in csv.DictReader(f)])
        if include_threads:
            ids = get_thread_ids_from_ids(ids, mongodb)
        query = {"_id": {"$in": ids}}
    else:
        query["text"] = re.compile(sys.argv[1].replace(' ', '\s+'), re.I)
elif len(sys.argv) > 2:
    query["$or"] = []
    for arg in sys.argv[1:]:
        query["$or"].append({"text": re.compile(arg.replace(' ', '\s+'), re.I)})

if not limit:
    count = mongodb.count(query)
else:
    count = limit
iterator = yield_csv(mongodb.find(query, sort=[("timestamp", 1)], limit=count), extra_fields=EXTRA_FIELDS)
if verbose:
    import progressbar
    bar = progressbar.ProgressBar(max_value=count)
    iterator = bar(iterator)
for t in iterator:
    print t
