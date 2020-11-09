#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import csv
import json
from gazouilloire.database.elasticmanager import ElasticManager, helpers
from gazouilloire.web.export import yield_csv


def export_csv(conf, query, verbose, export_threads_from_file):
    THREADS = conf.get('grab_conversations', False)
    EXTRA_FIELDS = conf.get('export', {}).get('extra_fields', [])

    try:
        db = ElasticManager(**conf['database'])
        db.prepare_indices()
    except Exception as e:
        sys.stderr.write(
            "ERROR: Could not initiate connection to database: %s %s" % (type(e), e))
        sys.exit(1)

    if len(query) == 1:
        query = query[0]
        if '{' in query:
            try:
                body = {
                    "query": {
                        "match": query
                    }
                }
            except Exception as e:
                sys.stderr.write(
                    "WARNING: query wrongly formatted: %s\n" % query)
                sys.exit("%s: %s\n" % (type(e), e))
        else:
            body = {
                "query": {
                    "match": {
                        "text": query
                    }
                }
            }

    elif len(query) > 1:
        body = {
            "query": {
                "bool": {
                    "filter": [{
                        "bool": {
                            "should": [{"term": {"text": arg}} for arg in query]
                        }
                    }]
                }
            }
        }

    elif len(query) == 0:
        if export_threads_from_file:
            with open(export_threads_from_file) as f:
                ids = sorted([t.get("id", t.get("_id"))
                              for t in csv.DictReader(f)])
                ids = db.get_thread_ids_from_ids(ids)
            body = ids
        else:
            body = {
                "query": {
                    "match_all": {}
                }
            }


    if isinstance(body, list):
        count = len(body)
        iterator = yield_csv(db.multi_get(body))
    else:
        count = db.client.count(index=db.tweets, doc_type='tweet', body=body)['count']
        body["sort"] = ["_id"]
        iterator = yield_csv(helpers.scan(client=db.client, index=db.tweets, query=body, preserve_order=True), extra_fields=EXTRA_FIELDS)
    if verbose:
        import progressbar
        bar = progressbar.ProgressBar(max_value=count)
        iterator = bar(iterator)
    for t in iterator:
        print(t)