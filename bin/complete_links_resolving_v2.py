#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import json
import click
from urllib3 import Timeout
from datetime import datetime
from pymongo import MongoClient, ASCENDING
from pymongo.errors import BulkWriteError
from minet import multithreaded_resolve
from minet.exceptions import RedirectError
from gazouilloire.database.elasticmanager import ElasticManager

BATCH_SIZE = 1000
with open('config.json') as confile:
    conf = json.loads(confile.read())


def prepare_db(host, port, db_name):
    try:
        db = ElasticManager(host, port, db_name)
        db_exists = db.exists(db.tweets)
    except Exception as e:
        sys.stderr.write(
            "ERROR: Could not initiate connection to database: %s %s" % (type(e), e))
        sys.exit(1)
    if db_exists:
        return db
    else:
        sys.stderr.write(
            "ERROR: elasticsearch index %s does not exist" % db_name
        )


def count_and_log(db, batch_size, done=0, skip=0):
    todo = list(db.find_tweets_with_unresolved_links(batch_size=batch_size))
    left = db.count_tweets("links_to_resolve", True)
    if done:
        done = "(+%s actual redirections resolved out of %s)" % (done, len(todo))
    t = datetime.now().isoformat()
    print("\n- [%s] RESOLVING LINKS: %s waiting (done:%s skipped:%s)\n" % (t, left, done or "", skip))
    return todo, left


@click.command()
@click.argument('batch_size', default=BATCH_SIZE)
@click.argument('db_name', default=conf["database"]["db_name"])
@click.argument('host', default=conf["database"]["host"])
@click.argument('port', default=conf["database"]["port"])
@click.option('--verbose/--silent', default=False)
def resolve(batch_size, db_name, host, port, verbose):
    db = prepare_db(host, port, db_name)

    skip = 0
    todo, left = count_and_log(db, batch_size, skip=skip)
    while todo:
        done = 0
        batch_urls = list(set([l for t in todo if not t.get("proper_links", []) for l in t.get('links', [])]))
        alreadydone = {l["link_id"]: l["real"] for l in db.find_links_in(batch_urls, batch_size)}
        urls_to_clear = []
        for u in batch_urls:
            if u in alreadydone:
                continue
            if u.startswith("https://twitter.com/") and "/status/" in u:
                alreadydone[u] = u.replace("?s=19", "")
                continue
            urls_to_clear.append(u)
        links_to_save = []
        t = datetime.now().isoformat()
        print("  + [%s] %s urls to resolve" % (t, len(urls_to_clear)))
        # try:
        for res in multithreaded_resolve(
          urls_to_clear,
          threads=min(50, batch_size),
          throttle=0.2,
          max_redirects=20,
          insecure=True,
          timeout=Timeout(connect=10, read=30),
          follow_meta_refresh=True
        ):
            source = res.url
            last = res.stack[-1]
            if res.error and type(res.error) != RedirectError and not issubclass(type(res.error), RedirectError):
                print("ERROR on resolving %s: %s (last url: %s)" % (source, res.error, last.url), file=sys.stderr)
                continue
            if verbose:
                print("          ", last.status, "(%s)" % last.type, ":", source, "->", last.url, file=sys.stderr)
            if len(source) < 1024:
                links_to_save.append({'link_id': source, 'real': last.url})
            alreadydone[source] = last.url
            if source != last.url:
                done += 1

        # except Exception as e:
        #     print("CRASHED with %s (%s) while resolving batch, skipping it for now..." % (e, type(e)))
        #     print("CRASHED with %s (%s) while resolving %s" % (e, type(e), urls_to_clear), file=sys.stderr)
        #     skip += batch_size
        #     print("  + [%s] STORING %s REDIRECTIONS IN MONGO" % (t, len(links_to_save)))
        #     if links_to_save:
        #         db.bulk_links(links_to_save)
        #     todo, left = count_and_log(db, batch_size, skip=skip)
        #     continue

        t = datetime.now().isoformat()
        print("  + [%s] STORING %s REDIRECTIONS IN ELASTIC" % (t, len(links_to_save)))
        if links_to_save:
            db.bulk_links(links_to_save)

        t = datetime.now().isoformat()
        print("  + [%s] UPDATING TWEETS LINKS IN ELASTIC" % t)
        tweets_already_done = []
        ids_done_in_batch = set()
        to_update = []
        for tweet in todo:
            if tweet.get("proper_links", []):
                tweets_already_done.append(tweet["_id"])
                continue
            tweetid = tweet.get('retweet_id') or tweet['_id']
            if tweetid in ids_done_in_batch:
                continue
            gdlinks = []
            for link in tweet.get("links", []):
                if link not in alreadydone:
                    break
                gdlinks.append(alreadydone[link])
            if len(gdlinks) != len(tweet.get("links", [])):
                skip += 1
                continue
            if tweet["retweet_id"] is None: # The tweet is an original tweet. It won't be found by the retweet search.
                to_update.append(
                    {'_id': tweet["_id"], "_source": {"doc": {'proper_links': gdlinks, 'links_to_resolve': False}}})
            # Search retweets and update them.
            db.update_links_if_retweet(tweetid, gdlinks)
            ids_done_in_batch.add(tweetid)

        # # clear tweets potentially rediscovered
        # if tweets_already_done:
        #     tweetscoll.update({"_id": {"$in": tweets_already_done}}, {"$set": {"links_to_resolve": False}},
        #                       upsert=False, multi=True)
        db.bulk_update_tweets(to_update)
        todo, left = count_and_log(db, batch_size, skip=skip)


if __name__ == '__main__':
    resolve()
