#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import csv
import gzip
import json
from datetime import datetime
from dateutil import relativedelta
from gazouilloire.database.elasticmanager import ElasticManager, helpers, DB_MAPPINGS
from gazouilloire.exports.tweet_fields import TWEET_FIELDS
from twitwi.constants import TWEET_FIELDS_TCAT
from twitwi import transform_tweet_into_csv_dict, apply_tcat_format
from twitwi.utils import custom_get_normalized_hostname
from gazouilloire.config_format import log
from casanova import reverse_reader
from casanova.exceptions import MissingColumnError
from elasticsearch.exceptions import RequestError


def date_to_timestamp(date):
    return str(date.timestamp())


def post_process_tweet_from_elastic(source):
    domains = [
        custom_get_normalized_hostname(l, normalize_amp=False, infer_redirection=False) for l in source.get(
            "proper_links", source.get("links", "")
        )
    ]
    source["domains"] = domains
    return source


def yield_csv(queryiterator, fmt, last_ids=set(), export_list=False, query_fields=None):
    for t in queryiterator:
        try:
            source = t["_source"]
        except KeyError:
            log.error(t)
            if not t["found"]:
                log.warning(t["_id"] + " not found in database")
                source = {"_id": t["_id"]}

        # ignore tweets only caught on deletion missing most fields
        # if export_list or (len(source) >= 10 and t["_id"] not in last_ids):
        if export_list or t["_id"] not in last_ids:
            if fmt == "tcat":
                source = apply_tcat_format(post_process_tweet_from_elastic(source))
            else:
                source = post_process_tweet_from_elastic(source)
            transform_tweet_into_csv_dict(
                source,
                item_id=t["_id"],
                allow_erroneous_plurals=True
            )
            yield source


def build_body(query, exclude_threads, exclude_retweets, query_fields=None, since=None, until=None, resume=False,
               lucene=False):
    if len(query) == 0 and not exclude_threads and not exclude_retweets and not since and not until and not resume:
        body = {
            "query": {
                "match_all": {}
            }
        }

        if query_fields:
            body["_source"] = query_fields

        return body

    body = {
        "query": {
            "bool": {
                "filter": [
                ]
            }
        }
    }

    if query_fields:
        body["_source"] = query_fields

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
    with open_file(outputfile, "r") as f:
        rev_reader = reverse_reader(f)
        for row in rev_reader:
            if row[rev_reader.headers.local_time] == last_time:
                last_ids.add(row[rev_reader.headers.id])
        return last_time, last_ids


def export_csv(conf, query, exclude_threads, exclude_retweets, since, until,
               verbose, export_threads_from_file, export_tweets_from_file, selection, fmt, outputfile, resume,
               lucene,
               step=None,
               index=None,
               sort_key="timestamp_utc"
               ):
    threads = conf.get('grab_conversations', False)

    sort_key = check_elastic_fields(sort_key, sort=True) if sort_key != "no" else ["_doc"]
    if "id" in sort_key:
        log.error("Sorting by id is not a valid option.")
        sys.exit(1)

    query_fields = None
    if selection:
        headers = check_elastic_fields(selection)
        if "domains" in headers:
            unique_fields = set(headers)
            query_fields = list(unique_fields.union({"links", "proper_links"}))
        elif query_fields != ["id"]:
            query_fields = headers
    else:
        if fmt == "v1":
            headers = TWEET_FIELDS
        else:
            headers = TWEET_FIELDS_TCAT
    if resume:
        with open_file(outputfile, "r") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            if sorted(fieldnames) == sorted(headers):
                headers = fieldnames
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
        iterator = yield_csv(db.multi_get(body, index), fmt, export_list=True)
    else:
        last_ids = set()
        if resume:
            last_timestamp, last_ids = find_potential_duplicate_ids(outputfile)
            since = datetime.fromisoformat(last_timestamp)
        body = build_body(query, exclude_threads, exclude_retweets, query_fields, since, until, lucene=lucene)
        try:
            count = multiindex_count(db, body, index, since, until)
        except RequestError as e:
            log.error("Query wrongly formatted. {}".format(str(e)))
            if lucene:
                log.error(
                    "Please read ElasticSearch's documentation regarding Lucene queries: "
                    "https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl-query-string-query.html")
            sys.exit(1)
        if step:
            iterator = yield_csv(
                yield_step_scans(db, step, since, until, query, exclude_threads, exclude_retweets, query_fields, index,
                                 lucene, sort_key),
                fmt,
                last_ids=last_ids
            )
        else:
            body["sort"] = sort_key
            iterator = yield_csv(
                yield_scans(db, body, since, until, index, sort_key),
                fmt,
                last_ids=last_ids
            )
    if verbose:
        from tqdm import tqdm
        iterator = tqdm(iterator, total=count)

    if resume:
        file = open_file(outputfile, 'a')
    else:
        file = open_file(outputfile, 'w') if outputfile else sys.stdout
    writer = csv.DictWriter(file, fieldnames=headers, restval='', quoting=csv.QUOTE_MINIMAL, extrasaction='ignore')
    if not resume:
        writer.writeheader()
    for t in iterator:
        writer.writerow(t)
    file.close()
    iterator.close()


def increment_steps(start_date, step):
    return start_date + relativedelta.relativedelta(**{step: 1})


def get_relevant_indices(db, index_param, since, until, sort_key=["timestamp_utc"]):
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
        relevant_indices = [index for index in relevant_indices if min_index <= index <= max_index]
        if sort_key == ["timestamp_utc"] or sort_key == ["_doc"] or len(relevant_indices) == 1:
            return relevant_indices
        if index_param and "," in index_param:
            log.warning("Sorting cannot be performed on several indices, only the tweets from {} will be exported."
                        .format(relevant_indices[0]))
            return [relevant_indices[0]]
        return [db.tweets + "*"]

    return [db.tweets]


def yield_step_scans(db, step, global_since, until, query, exclude_threads, exclude_retweets, query_fields, index_param,
                     lucene, sort_key):
    for index_name in get_relevant_indices(db, index_param, global_since, until, sort_key):
        if db.multi_index and (sort_key == ["timestamp_utc"] or sort_key == ["_doc"]):
            index_expression = datetime.strptime(index_name, db.tweets + "_%Y_%m").strftime("%Y-%m")
        else:
            index_expression = None
        for since, body in time_step_iterator(db, step, global_since, until, query, exclude_threads, exclude_retweets,
                                              index_expression, lucene, query_fields):
            body["sort"] = sort_key
            for t in helpers.scan(client=db.client, index=index_name, query=body, preserve_order=True):
                yield t


def yield_scans(db, body, since, until, index_param, sort_key):
    for index_name in get_relevant_indices(db, index_param, since, until, sort_key):
        for t in helpers.scan(client=db.client, index=index_name, query=body, preserve_order=True):
            yield t


def time_step_iterator(db, step, since, until, query, exclude_threads, exclude_retweets, index_param,
                       lucene, query_fields=None):
    if not until:
        until = datetime.now()
    if not since:
        body = build_body(query, exclude_threads, exclude_retweets, ["timestamp_utc"], lucene=lucene)
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
        body = build_body(query, exclude_threads, exclude_retweets, query_fields, since, one_more_step, lucene=lucene)
        yield since, body
        since = increment_steps(since, step)
        one_more_step = increment_steps(since, step)


def multiindex_count(db, body, index_param, since, until):
    count = 0
    count_body = {"query": body["query"]}
    for index_name in get_relevant_indices(db, index_param, since, until):
        count += db.client.count(index=index_name, body=count_body)['count']
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


def check_elastic_fields(fields, sort=False):
    field_list = fields.split(",")
    mapping = DB_MAPPINGS["tweets_mapping"]["mappings"]["properties"]
    for field in field_list:

        if field not in mapping and field != "id":
            log.error("Field '{}' not in elasticsearch mapping, are you sure that you spelled it correctly?"
                      .format(field))
            sys.exit(1)

        if sort and mapping[field]["type"] == "text":
            log.error("Sorting by textual fields such as '{}' is not a valid option.".format(field))
            sys.exit(1)

    return field_list


def open_file(outputfile, mode):
    filename, file_extension = os.path.splitext(outputfile)
    if file_extension == ".gz" or file_extension == ".gzip":
        log.error("gzip format is not handled for now")
        sys.exit(1)
        return gzip.open(outputfile, mode+"t", newline='')
    return open(outputfile, mode, newline='')
