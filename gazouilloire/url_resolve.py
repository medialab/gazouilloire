#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import re
from urllib3 import Timeout
from datetime import datetime
from elasticsearch import helpers
from minet import multithreaded_resolve
from minet.exceptions import RedirectError
from gazouilloire.database.elasticmanager import ElasticManager
from ural.get_domain_name import get_hostname_prefixes
from twitwi.utils import custom_get_normalized_hostname, custom_normalize_url
from gazouilloire.config_format import log
import logging


def count_and_log(db, batch_size, done=0, skip=0, retry_days=30):
    db.client.indices.refresh(index=db.tweets)
    todo = list(db.find_tweets_with_unresolved_links(batch_size=batch_size, retry_days=retry_days))
    left = db.count_tweets("links_to_resolve", True)
    if done:
        done = "(+%s actual redirections resolved out of %s)" % (done, len(todo))
    log.info("RESOLVING LINKS: %s waiting (done:%s skipped:%s)\n" % (left, done or "", skip))
    return todo


def resolve_loop(batch_size, db, todo, skip, verbose, url_debug, retry_days=30):
    if verbose:
        log.setLevel(logging.DEBUG)
    if url_debug:
        fh = logging.FileHandler('url_resolve.log')
        fh.setLevel(logging.DEBUG)
        log.addHandler(fh)
    done = 0
    batch_urls = list(set([l for t in todo if not t.get("proper_links", []) for l in t.get('links', [])]))
    alreadydone = {
        l["link_id"]: (
            l["real"],
            get_hostname_prefixes(custom_get_normalized_hostname(l["real"]))
        ) for l in db.find_links_in(batch_urls, batch_size)
    }
    urls_to_clear = []
    for u in batch_urls:
        if u in alreadydone:
            continue
        if u.startswith("https://twitter.com/") and "/status/" in u:
            alreadydone[u] = (re.sub(r"\?s=\d+", "", u), ["twitter.com", "com"])
            continue
        urls_to_clear.append(u)
    if urls_to_clear:
        links_to_save = []
        log.info("%s urls to resolve" % (len(urls_to_clear)))
        if url_debug:
            for url in urls_to_clear:
                log.info(url)
        try:
            for res in multithreaded_resolve(
                    urls_to_clear,
                    threads=50,
                    throttle=0.2,
                    max_redirects=20,
                    insecure=True,
                    timeout=Timeout(connect=10, read=30),
                    follow_meta_refresh=True
            ):
                source = res.url
                last = res.stack[-1]
                normalized_url = custom_normalize_url(last.url)
                domain = get_hostname_prefixes(custom_get_normalized_hostname(normalized_url))
                if res.error and type(res.error) != RedirectError and not issubclass(type(res.error), RedirectError):
                    if not url_debug and retry_days:
                        log.warning("failed to resolve (will retry) %s: %s (last url: %s)" % (source, res.error, last.url)
                                  )
                        continue
                    # TODO:
                    #  Once redis db is effective, set a timeout on keys on error (https://redis.io/commands/expire)
                if last.status == 200:
                    log.debug("{} {}: {} --> {}".format(last.status, last.type,  source, normalized_url))
                else:
                    log.warning("{} {}: {} --> {}".format(last.status, last.type, source, normalized_url))
                links_to_save.append({'link_id': source, 'real': normalized_url, 'domains': domain})
                alreadydone[source] = (normalized_url, domain)
                if source != normalized_url:
                    done += 1
        except Exception as e:
            log.error("CRASHED with %s (%s) while resolving batch, skipping it for now..." % (e, type(e)))
            log.error("CRASHED with %s (%s) while resolving %s" % (e, type(e), urls_to_clear))
            if url_debug:
                for url in urls_to_clear:
                    normalized_url = custom_normalize_url(url)
                    domain = get_hostname_prefixes(custom_get_normalized_hostname(normalized_url))
                    links_to_save.append({'link_id': url, 'real': normalized_url, 'domains': domain})
                    alreadydone[url] = (normalized_url, domain)
                    if url != normalized_url:
                        done += 1
            else:
                skip += batch_size
                log.info("STORING %s REDIRECTIONS IN ELASTIC" % (len(links_to_save)))
                if links_to_save:
                    helpers.bulk(db.client, actions=db.prepare_indexing_links(links_to_save))
                return done, skip

        log.info("STORING %s REDIRECTIONS IN ELASTIC" % (len(links_to_save)))
        if links_to_save:
            helpers.bulk(db.client, actions=db.prepare_indexing_links(links_to_save))

        log.info("UPDATING TWEETS LINKS IN ELASTIC")
    tweets_already_done = []
    ids_done_in_batch = set()
    to_update = []
    for tweet in todo:
        if tweet.get("proper_links", []):
            tweets_already_done.append(tweet["_id"])
            continue
        tweetid = tweet.get('retweeted_id') or tweet['_id']
        if tweetid in ids_done_in_batch:
            continue
        gdlinks = []
        gddomains = set()
        for link in tweet.get("links", []):
            if link not in alreadydone:
                break
            gdlinks.append(alreadydone[link][0])
            gddomains.update(set(alreadydone[link][1]))
        if len(gdlinks) != len(tweet.get("links", [])):
            skip += 1
            continue
        if tweet.get("retweeted_id") is None:  # The tweet is an original tweet. No need to search for its id.
            to_update.append(
                {'_id': tweet["_id"], "_source": {"doc": {
                    'proper_links': gdlinks,
                    'links_to_resolve': False,
                    'domains': list(gddomains)
                }}})
        db.update_retweets_with_links(tweetid, gdlinks, list(gddomains))
        ids_done_in_batch.add(tweetid)

        # # clear tweets potentially rediscovered
        # if tweets_already_done:
        #     tweetscoll.update({"_id": {"$in": tweets_already_done}}, {"$set": {"links_to_resolve": False}},
        #                       upsert=False, multi=True)
    helpers.bulk(db.client, actions=db.prepare_updating_links_in_tweets(to_update))

    return done, skip
