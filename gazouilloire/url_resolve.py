#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from urllib3 import Timeout
from datetime import datetime
from elasticsearch import helpers
from minet import multithreaded_resolve
from minet.exceptions import RedirectError
from gazouilloire.database.elasticmanager import ElasticManager
from ural import normalize_url


def count_and_log(db, batch_size, done=0, skip=0):
    db.client.indices.refresh(index=db.tweets)
    todo = list(db.find_tweets_with_unresolved_links(batch_size=batch_size))
    left = db.count_tweets("links_to_resolve", True)
    if done:
        done = "(+%s actual redirections resolved out of %s)" % (done, len(todo))
    t = datetime.now().isoformat()
    print("\n- [%s] RESOLVING LINKS: %s waiting (done:%s skipped:%s)\n" % (t, left, done or "", skip))
    return todo


def normalize(url):
    return normalize_url(url, strip_authentication=False, strip_trailing_slash=False, strip_protocol=False,
                         strip_irrelevant_subdomains=False, strip_fragment=False, normalize_amp=False,
                         fix_common_mistakes=False, infer_redirection=False, quoted=True)


def resolve_loop(batch_size, db, todo, skip, verbose):
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
    if urls_to_clear:
        links_to_save = []
        t = datetime.now().isoformat()
        print("  + [%s] %s urls to resolve" % (t, len(urls_to_clear)))
        try:
            for res in multithreaded_resolve(
                    urls_to_clear,
                    threads=min(50, len(urls_to_clear)),
                    throttle=0.2,
                    max_redirects=20,
                    insecure=True,
                    timeout=Timeout(connect=10, read=30),
                    follow_meta_refresh=True
            ):
                source = res.url
                last = res.stack[-1]
                normalized_url = normalize(last.url)
                if res.error and type(res.error) != RedirectError and not issubclass(type(res.error), RedirectError):
                    print("ERROR on resolving %s: %s (last url: %s)" % (source, res.error, last.url), file=sys.stderr)
                    # TODO:
                    #  Once redis db is effective, set a timeout on keys on error (https://redis.io/commands/expire)
                if verbose:
                    print("          ", last.status, "(%s)" % last.type, ":", source, "->", normalized_url, file=sys.stderr)
                links_to_save.append({'link_id': source, 'real': normalized_url})
                alreadydone[source] = normalized_url
                if source != normalized_url:
                    done += 1
        except Exception as e:
            print("CRASHED with %s (%s) while resolving batch, skipping it for now..." % (e, type(e)))
            print("CRASHED with %s (%s) while resolving %s" % (e, type(e), urls_to_clear), file=sys.stderr)
            skip += batch_size
            print("  + [%s] STORING %s REDIRECTIONS IN ELASTIC" % (t, len(links_to_save)))
            if links_to_save:
                helpers.bulk(db.client, actions=db.prepare_indexing_links(links_to_save))
            return done, skip

        t = datetime.now().isoformat()
        print("  + [%s] STORING %s REDIRECTIONS IN ELASTIC" % (t, len(links_to_save)))
        if links_to_save:
            helpers.bulk(db.client, actions=db.prepare_indexing_links(links_to_save))

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
        if tweet["retweet_id"] is None:  # The tweet is an original tweet. No need to search for its id.
            to_update.append(
                {'_id': tweet["_id"], "_source": {"doc": {'proper_links': gdlinks, 'links_to_resolve': False}}})
        db.update_retweets_with_links(tweetid, gdlinks)
        ids_done_in_batch.add(tweetid)

        # # clear tweets potentially rediscovered
        # if tweets_already_done:
        #     tweetscoll.update({"_id": {"$in": tweets_already_done}}, {"$set": {"links_to_resolve": False}},
        #                       upsert=False, multi=True)
        helpers.bulk(db.client, actions=db.prepare_updating_links_in_tweets(to_update))

    return done, skip