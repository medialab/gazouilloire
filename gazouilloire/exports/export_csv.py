#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import csv
from gazouilloire.database.elasticmanager import ElasticManager, helpers
from gazouilloire.web.export import TWEET_FIELDS
from gazouilloire.config_format import log


def yield_csv(queryiterator):
    for t in queryiterator:
        try:
            source = t["_source"]
        except KeyError:
            if not t["found"]:
                log.error(t["_id"] + " not found in database")
                continue
        # ignore tweets only caught on deletion missing most fields
        if len(source) < 10:
            continue
        source["id"] = t["_id"]
        source["links"] = source.get("proper_links", source.get("links", []))
        for multiple in ["links", "hashtags", "collected_via", "media_urls", "media_files", "mentioned_names", "mentioned_ids"]:
            source[multiple] = "|".join(source[multiple])
        for boolean in ["possibly_sensitive", "user_verified", "match_query"]:
            source[boolean] = int(source[boolean]) if boolean in source else ''

        yield source

def export_csv(conf, query, exclude_threads, verbose, export_threads_from_file, selection):
    THREADS = conf.get('grab_conversations', False)
    EXTRA_FIELDS = conf.get('export', {}).get('extra_fields', [])
    SELECTION = conf.get('export', {}).get('fields', [])+EXTRA_FIELDS if selection else TWEET_FIELDS+EXTRA_FIELDS

    try:
        db = ElasticManager(**conf['database'])
        db.prepare_indices()
    except Exception as e:
        sys.stderr.write(
            "ERROR: Could not initiate connection to database: %s %s" % (type(e), e))
        sys.exit(1)

    if not THREADS:
        exclude_threads = False

    body = {
            "query": {
                "bool": {
                    "filter": [
                    ]
                }
            }
        }
    filter = body["query"]["bool"]["filter"]
    exclude_clause = {"term": {"match_query": True}}

    if len(query) == 1:
        query = query[0]
        if '{' in query:
            try:
                query = eval(query)
            except Exception as e:
                sys.stderr.write(
                    "WARNING: query wrongly formatted: %s\n" % query)
                sys.exit("%s: %s\n" % (type(e), e))
            filter.append({"term": query})
        else:
            filter.append({"term": {"text": query}})
        if exclude_threads:
            filter.append(exclude_clause)

    elif len(query) > 1:
        filter.append({"bool": {"should": [{"term": {"text": arg}} for arg in query]}})
        if exclude_threads:
            filter.append(exclude_clause)

    elif len(query) == 0:
        if export_threads_from_file:
            with open(export_threads_from_file) as f:
                ids = sorted([t.get("id", t.get("_id"))
                              for t in csv.DictReader(f)])
                ids = db.get_thread_ids_from_ids(ids)
            body = ids
        else:
            if exclude_threads:
                filter.append(exclude_clause)
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
        iterator = yield_csv(helpers.scan(client=db.client, index=db.tweets, query=body, preserve_order=True))
    if verbose:
        import progressbar
        bar = progressbar.ProgressBar(max_value=count)
        iterator = bar(iterator)
    writer = csv.DictWriter(sys.stdout, fieldnames=SELECTION, restval='', quoting=csv.QUOTE_MINIMAL,
                            extrasaction='ignore')
    writer.writeheader()
    for t in iterator:
        writer.writerow(t)