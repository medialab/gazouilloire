#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import csv
import json
from datetime import datetime
from dateutil import relativedelta
from gazouilloire.database.elasticmanager import ElasticManager, helpers, DB_MAPPINGS
from twitwi import transform_tweet_into_csv_dict
from twitwi.utils import custom_get_normalized_hostname
from twitwi.constants import TWEET_FIELDS
from gazouilloire.config_format import log
from casanova import reverse_reader
from casanova.exceptions import MissingColumnError
from elasticsearch.exceptions import RequestError


def date_to_timestamp(date):
    return str(date.timestamp())


def post_process_tweet_from_elastic(source):
    domains = [
        custom_get_normalized_hostname(l, normalize_amp=False, infer_redirection=False) for l in source.get(
            "proper_links", source["links"]
        )
    ]
    source["domains"] = domains
    return source


def yield_csv(queryiterator, last_ids=set(), export_list=False):
    for t in queryiterator:
        try:
            source = t["_source"]
        except KeyError:
            if not t["found"]:
                log.warning(t["_id"] + " not found in database")
                source = {"_id": t["_id"]}

        # ignore tweets only caught on deletion missing most fields
        if export_list or (len(source) >= 10 and t["_id"] not in last_ids):
            transform_tweet_into_csv_dict(
                post_process_tweet_from_elastic(source), item_id=t["_id"], allow_erroneous_plurals=True
            )
            yield source


def build_body(query, exclude_threads, exclude_retweets, since=None, until=None, outputfile=None, resume=False,
               lucene=False):
    if len(query) == 0 and not exclude_threads and not exclude_retweets and not since and not until and not resume:
        body = {
            "query": {
                "match_all": {}
            }
        }
        return body

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
            range_clause["range"]["timestamp_utc"]["gte"] = date_to_timestamp(since)
        if until:
            range_clause["range"]["timestamp_utc"]["lt"] = date_to_timestamp(until)
        filter.append(range_clause)

    if len(query) == 1:
        query = query[0]
        if '{' in query:
            try:
                query = json.loads(query)
            except Exception as e:
                log.error("query wrongly formatted: %s\n" % query)
                sys.exit("%s: %s\n" % (type(e), e))
            if "id" in query:
                query = {"_id": query["id"]}
            filter.append({"term": query})
        elif ' AND ' in query or ' OR ' in query or lucene:
            filter.append({
                "query_string": {
                    "query": query,
                    "default_field": "text"
                }
            })
        else:
            filter.append({"term": {"text": query.lower()}})

    elif len(query) > 1:
        if lucene:
            log.error("Query wrongly formatted: use quotes to do a lucene query with several words.")
            sys.exit(1)
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
        if db.multi_index:
            if db.exists(db.tweets + "_*"):
                return db
        else:
            if db.exists(db.tweets):
                return db
        log.error("Elasticsearch database does not exist")
        sys.exit(1)
    except Exception as e:
        log.error("Could not initiate connection to database: %s %s" % (type(e), e))
        sys.exit(1)


def find_potential_duplicate_ids(outputfile):
    last_ids = set()
    try:
        last_time = reverse_reader.last_cell(outputfile, 'local_time')
    except MissingColumnError:
        log.error("A 'local_time' column is missing in file {} in order to use the --resume/-r option".format(
            outputfile
        ))
        sys.exit(1)
    with open(outputfile, "r") as f:
        rev_reader = reverse_reader(f)
        for row in rev_reader:
            if row[rev_reader.headers.local_time] == last_time:
                last_ids.add(row[rev_reader.headers.id])
            else:
                return last_time, last_ids


def export_csv(conf, query, exclude_threads, exclude_retweets, since, until,
               verbose, export_threads_from_file, export_tweets_from_file, selection, outputfile, resume, lucene,
               step=None,
               index=None
               ):
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
    if resume:
        with open(outputfile, "r") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            if sorted(fieldnames) == sorted(SELECTION):
                SELECTION = fieldnames
            else:
                log.error("The column names in the {} file do not match the export format".format(outputfile))
                sys.exit(1)

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

    if export_tweets_from_file:
        if len(query) > 0:
            log.error("--export_tweets_from_file option is not compatible with a keyword query")
            sys.exit(1)
        with open(export_tweets_from_file) as f:
            body = sorted([t.get("id", t.get("_id")) for t in csv.DictReader(f)])

    if export_threads_from_file or export_tweets_from_file:
        count = len(body)
        iterator = yield_csv(db.multi_get(body, index), export_list=True)
    else:
        last_ids = set()
        if resume:
            last_timestamp, last_ids = find_potential_duplicate_ids(outputfile)
            since = datetime.fromisoformat(last_timestamp)
        body = build_body(query, exclude_threads, exclude_retweets, since, until, lucene=lucene)
        try:
            count = multiindex_count(db, body, index, since, until)
        except RequestError:
            log.error("Query wrongly formatted.")
            if lucene:
                log.error(
                    "Please read ElasticSearch's documentation regarding Lucene queries: https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl-query-string-query.html")
            sys.exit(1)
        if step:
            iterator = yield_csv(
                yield_step_scans(db, step, since, until, query, exclude_threads, exclude_retweets, index, lucene),
                last_ids=last_ids
            )
        else:
            body["sort"] = ["timestamp_utc"]
            iterator = yield_csv(
                yield_scans(db, body, since, until, index),
                last_ids=last_ids
            )
    if verbose:
        import progressbar
        bar = progressbar.ProgressBar(max_value=count)
        iterator = bar(iterator)

    if resume:
        file = open(outputfile, 'a', newline='')
    else:
        file = open(outputfile, 'w', newline='') if outputfile else sys.stdout
    writer = csv.DictWriter(file, fieldnames=SELECTION, restval='', quoting=csv.QUOTE_MINIMAL, extrasaction='ignore')
    if not resume:
        writer.writeheader()
    for t in iterator:
        writer.writerow(t)
    file.close()


def increment_steps(start_date, step):
    return start_date + relativedelta.relativedelta(**{step: 1})


def get_relevant_indices(db, index_param, since, until):
    """
    return all open indices between since and until
    """
    if db.multi_index:
        if index_param:
            relevant_indices = db.get_valid_index_names(index_param, include_closed_indices=False)
        else:
            relevant_indices = db.get_sorted_indices(include_closed_indices=False)
        if len(relevant_indices) == 0:
            return []
        min_index = relevant_indices[0]
        max_index = relevant_indices[-1]
        if since:
            min_index = db.get_index_name(since)
        if until:
            max_index = db.get_index_name(until)
        return [index for index in relevant_indices if min_index <= index <= max_index]
    return [db.tweets]


def yield_step_scans(db, step, global_since, until, query, exclude_threads, exclude_retweets, index_param, lucene):
    for index_name in get_relevant_indices(db, index_param, global_since, until):
        if db.multi_index:
            index_expression = datetime.strptime(index_name, db.tweets + "_%Y_%m").strftime("%Y-%m")
        else:
            index_expression = None
        for since, body in time_step_iterator(db, step, global_since, until, query, exclude_threads, exclude_retweets,
                                              index_expression, lucene):
            body["sort"] = ["timestamp_utc"]
            for t in helpers.scan(client=db.client, index=index_name, query=body, preserve_order=True):
                yield t


def yield_scans(db, body, since, until, index_param):
    for index_name in get_relevant_indices(db, index_param, since, until):
        for t in helpers.scan(client=db.client, index=index_name, query=body, preserve_order=True):
            yield t


def time_step_iterator(db, step, since, until, query, exclude_threads, exclude_retweets, index_param, lucene):
    if not until:
        until = datetime.now()
    if not since:
        body = build_body(query, exclude_threads, exclude_retweets, lucene=lucene)
        body["sort"] = ["timestamp_utc"]
        body["size"] = 1
        if index_param:
            indices = db.get_valid_index_names(index_param, include_closed_indices=False)
        else:
            indices = [db.tweets + "*"]
        if len(indices) == 0:
            since = datetime.now()
        else:
            first_index = indices[0]
            first_tweet = db.client.search(body=body, index=first_index, size=1)["hits"]["hits"]
            if len(first_tweet) == 0:
                since = datetime.now()
            else:
                first_tweet = first_tweet[0]["_source"]
                since = datetime.fromtimestamp(first_tweet["timestamp_utc"])
    one_more_step = increment_steps(since, step)
    while since < until:
        body = build_body(query, exclude_threads, exclude_retweets, since, one_more_step, lucene=lucene)
        yield since, body
        since = increment_steps(since, step)
        one_more_step = increment_steps(since, step)


def multiindex_count(db, body, index_param, since, until):
    count = 0
    for index_name in get_relevant_indices(db, index_param, since, until):
        count += db.client.count(index=index_name, body=body)['count']
    return count


def count_by_step(conf, query, exclude_threads, exclude_retweets, since, until, outputfile, lucene, step=None,
                  index=None):
    db = call_database(conf)
    file = open(outputfile, 'w', newline='') if outputfile else sys.stdout
    writer = csv.writer(file)
    if step:
        for since, body in time_step_iterator(db, step, since, until, query, exclude_threads, exclude_retweets, index,
                                              lucene):
            count = multiindex_count(db, body, index, since, until)
            writer.writerow([",".join(query), since, count] if query else [since, count])
    else:
        body = build_body(query, exclude_threads, exclude_retweets, since, until, lucene=lucene)
        count = multiindex_count(db, body, index, since, until)
        writer.writerow([",".join(query), count] if query else [count])

    file.close()
