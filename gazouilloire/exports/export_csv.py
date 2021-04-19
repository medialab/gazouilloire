#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import csv
from datetime import datetime
from dateutil import relativedelta
from gazouilloire.database.elasticmanager import ElasticManager, helpers, DB_MAPPINGS
from twitwi import transform_tweet_into_csv_dict
from twitwi.constants import TWEET_FIELDS
from gazouilloire.config_format import log


def isodate_to_timestamp(isodate):
    return str(datetime.fromisoformat(isodate).timestamp())


def yield_csv(queryiterator):
    for t in queryiterator:
        try:
            source = t["_source"]
        except KeyError:
            if not t["found"]:
                log.error(t["_id"] + " not found in database")
                continue
        # ignore tweets only caught on deletion missing most fields
        if len(source) >= 10:
            transform_tweet_into_csv_dict(source, item_id=t["_id"])
            yield source


def build_body(query, exclude_threads, exclude_retweets, since=None, until=None):
    if len(query) == 0 and not exclude_threads and not exclude_retweets and not since and not until:
        body = {
            "query": {
                "match_all": {}
            }
        }

    else:
        body = {
            "query": {
                "bool": {
                    "filter": [
                    ]
                }
            }
        }
        filter = body["query"]["bool"]["filter"]
        if exclude_threads:
            filter.append({"term": {"match_query": True}})
        if exclude_retweets:
            body["query"]["bool"]["must_not"] = {"exists": {"field": "retweeted_id"}}
        if since or until:
            range_clause = {"range": {"timestamp_utc": {}}}
            if since:
                range_clause["range"]["timestamp_utc"]["gte"] = isodate_to_timestamp(since)
            if until:
                range_clause["range"]["timestamp_utc"]["lt"] = isodate_to_timestamp(until)
            filter.append(range_clause)

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
            elif ' AND ' in query or ' OR ' in query:
                filter.append({
                    "query_string": {
                        "query": query,
                        "default_field": "text"
                    }
                })
            else:
                filter.append({"term": {"text": query.lower()}})

        elif len(query) > 1:
            filter.append({"bool": {"should": []}})
            for arg in query:
                if ' AND ' in arg or ' OR ' in arg:
                    queryarg = {
                        "query_string": {
                            "query": arg,
                            "default_field": "text"
                        }
                    }
                else:
                    queryarg = {"term": {"text": arg.lower()}}
                filter[-1]["bool"]["should"].append(queryarg)

    return body

def call_database(conf):
    try:
        db = ElasticManager(**conf['database'])
        if db.exists(db.tweets):
            return db
        else:
            log.error("Elasticsearch database does not exist")
            sys.exit(1)
    except Exception as e:
        log.error("Could not initiate connection to database: %s %s" % (type(e), e))
        sys.exit(1)

def export_csv(conf, query, exclude_threads, exclude_retweets, since, until,
               verbose, export_threads_from_file, selection, outputfile):
    threads = conf.get('grab_conversations', False)
    if selection:
        SELECTION = selection.split(",")
        mapping = DB_MAPPINGS["tweets_mapping"]["mappings"]["properties"]
        for field in SELECTION:
            if field not in mapping and field != "id":
                log.warning("Field '{}' not in elasticsearch mapping, are you sure that you spelled it correctly?"
                            .format(field))
    else:
        SELECTION = TWEET_FIELDS

    db = call_database(conf)

    if not threads:
        exclude_threads = False

    if export_threads_from_file:
        if len(query) > 0:
            log.error("--export_threads_from_file option is not compatible with a keyword query")
            sys.exit(1)
        with open(export_threads_from_file) as f:
            ids = sorted([t.get("id", t.get("_id"))
                          for t in csv.DictReader(f)])
            ids = db.get_thread_ids_from_ids(ids)
        body = ids
    else:
        body = build_body(query, exclude_threads, exclude_retweets, since, until)

    if isinstance(body, list):
        count = len(body)
        iterator = yield_csv(db.multi_get(body))
    else:
        count = db.client.count(index=db.tweets, body=body)['count']
        body["sort"] = ["timestamp_utc"]
        iterator = yield_csv(helpers.scan(client=db.client, index=db.tweets, query=body, preserve_order=True))
    if verbose:
        import progressbar
        bar = progressbar.ProgressBar(max_value=count)
        iterator = bar(iterator)

    file = open(outputfile, 'w') if outputfile else sys.stdout
    writer = csv.DictWriter(file, fieldnames=SELECTION, restval='', quoting=csv.QUOTE_MINIMAL, extrasaction='ignore')
    writer.writeheader()
    for t in iterator:
        writer.writerow(t)
    file.close()


def increment_steps(start_date, step):
    return start_date + relativedelta.relativedelta(**{step: 1})


def count_by_step(conf, query, exclude_threads, exclude_retweets, since, until, outputfile, step=None):
    db = call_database(conf)
    file = open(outputfile, 'w') if outputfile else sys.stdout
    writer = csv.writer(file, quoting=csv.QUOTE_NONE)
    
    if step:
        until_dt = datetime.fromisoformat(until) if until else datetime.now()
        if not since:
            body = build_body(query, exclude_threads, exclude_retweets)
            body["sort"] = ["timestamp_utc"]
            body["size"] = 1
            first_tweet = db.client.search(body=body, index=db.tweets)["hits"]["hits"][0]["_source"]
            since = first_tweet["local_time"]
        since_dt = datetime.fromisoformat(since)
        one_more_step = increment_steps(since_dt, step)
        while since_dt < until_dt:
            body = build_body(query, exclude_threads, exclude_retweets, since_dt.isoformat(), one_more_step.isoformat())
            count = db.client.count(index=db.tweets, body=body)['count']
            writer.writerow([",".join(query), since_dt, count])
            since_dt = increment_steps(since_dt, step)
            one_more_step = increment_steps(since_dt, step)
    else:
        body = build_body(query, exclude_threads, exclude_retweets, since, until)
        count = db.client.count(index=db.tweets, body=body)['count']
        writer.writerow([",".join(query), count])

    file.close()
