#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import
import os
import sys
import re
import csv
import json
from gazouilloire.database.elasticmanager import ElasticManager, helpers
from gazouilloire.web.export import yield_csv, get_thread_ids_from_ids

try:
    with open(os.path.join(os.path.dirname(__file__), '..', 'config.json')) as confile:
        conf = json.loads(confile.read())
except Exception as e:
    sys.stderr.write("ERROR: Impossible to read config.json: %s %s" % (type(e), e))
    exit(1)
THREADS = conf.get('grab_conversations', False)
# TODO: Ask Benjamin what are these selected fields
# SELECTED_FIELD = conf.get('export', {}).get('selected_field', None)
EXTRA_FIELDS = conf.get('export', {}).get('extra_fields', [])

try:
    db = ElasticManager(**conf['database'])
    db.prepare_indices()
except Exception as e:
    sys.stderr.write(
        "ERROR: Could not initiate connection to database: %s %s" % (type(e), e))
    sys.exit(1)

verbose = True
if len(sys.argv) > 1 and "--quiet" in sys.argv:
    sys.argv.remove("--quiet")
    verbose = False

# only_selected = False
# if SELECTED_FIELD and len(sys.argv) > 1 and "--selected" in sys.argv:
#     sys.argv.remove("--selected")
#     only_selected = True

include_threads = True
if THREADS and len(sys.argv) > 1 and "--no-threads" in sys.argv:
    sys.argv.remove("--no-threads")
    include_threads = False

query = {}
# if only_selected:
#     query = {SELECTED_FIELD: True}
if len(sys.argv) == 2:
    if '{' in sys.argv[1]:
        try:
            query = {
                "query": {
                    "match": sys.argv[1]
                }
            }
            # if only_selected:
            #     query = {"$and": [query, {SELECTED_FIELD: True}]}
        except Exception as e:
            sys.stderr.write(
                "WARNING: query wrongly formatted: %s\n" % sys.argv[1])
            sys.exit("%s: %s\n" % (type(e), e))
    elif os.path.exists(sys.argv[1]):
        with open(sys.argv[1]) as f:
            ids = sorted([t.get("id", t.get("_id"))
                          for t in csv.DictReader(f)])
        if include_threads:
            ids = db.get_thread_ids_from_ids(ids)
        query = ids
    else:
        query = {
            "query": {
                "match": {
                    "text": sys.argv[1]
                }
            }
        }

elif len(sys.argv) > 2:
    query = {
        "query": {
            "bool": {
                "should": [{"term": {"text": arg}} for arg in sys.argv[1:]]
            }
        }
    }

else:
    query = {
        "query": {
            "match_all": {}
        }
    }

if isinstance(query, list):
    count = len(query)
    iterator = yield_csv(db.multi_get(query))
else:
    # count = db.count_tweets()
    count = db.client.count(index=db.tweets, doc_type='tweet', body={"query": {"match_all": {}}})['count']
    iterator = yield_csv(helpers.scan(client=db.client, index=db.tweets, query=query), extra_fields=EXTRA_FIELDS)
if verbose:
    import progressbar2
    bar = progressbar2.ProgressBar(max_value=count)
    iterator = bar(iterator)
for t in iterator:
    print(t)
