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

BATCH_SIZE = 1000
with open('config.json') as confile:
    conf = json.loads(confile.read())

def prepare_db(mongo_host, mongo_port, mongo_db):
    db = MongoClient(mongo_host, mongo_port)[mongo_db]
    linkscoll = db['links']
    tweetscoll = db['tweets']
    for f in ['retweet_id', 'in_reply_to_status_id_str', 'timestamp',
              'links_to_resolve', 'lang', 'user_lang', 'langs']:
        tweetscoll.ensure_index([(f, ASCENDING)], background=True)
    tweetscoll.ensure_index([('links_to_resolve', ASCENDING), ('_id', ASCENDING)], background=True)
    return linkscoll, tweetscoll

def count_and_log(tweetscoll, batch_size, done=0, skip=0):
    todo = list(tweetscoll.find({"links_to_resolve": True}, projection={"links": 1, "proper_links": 1, "retweet_id": 1}, limit=batch_size, sort=[("_id", 1)], skip=skip))
    left = tweetscoll.count({"links_to_resolve": True})
    if done:
        done = "(+%s actual redirections resolved out of %s)" % (done, len(todo))
    t = datetime.now().isoformat()
    print("\n- [%s] RESOLVING LINKS: %s waiting (done:%s skipped:%s)\n" % (t, left, done or "", skip))
    return todo, left

@click.command()
@click.argument('batch_size', default=BATCH_SIZE)
@click.argument('mongo_db', default=conf["mongo"]["db"])
@click.argument('mongo_host', default='localhost')
@click.argument('mongo_port', default=27017)
@click.option('--verbose/--silent', default=False)
def resolve(batch_size, mongo_db, mongo_host, mongo_port, verbose):
    linkscoll, tweetscoll = prepare_db(mongo_host, mongo_port, mongo_db)

    skip = 0
    todo, left = count_and_log(tweetscoll, batch_size, skip=skip)
    while todo:
        done = 0
        batch_urls = list(set([l for t in todo if not t.get("proper_links", []) for l in t.get('links', [])]))
        alreadydone = {l["_id"]: l["real"] for l in linkscoll.find({"_id": {"$in": batch_urls}})}
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
        try:
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
                    links_to_save.append({'_id': source, 'real': last.url})
                alreadydone[source] = last.url
                if source != last.url:
                    done += 1
        except Exception as e:
            print("CRASHED with %s (%s) while resolving batch, skipping it for now..." % (e, type(e)))
            print("CRASHED with %s (%s) while resolving %s" % (e, type(e), urls_to_clear), file=sys.stderr)
            skip += batch_size
            print("  + [%s] STORING %s REDIRECTIONS IN MONGO" % (t, len(links_to_save)))
            if links_to_save:
                try:
                    result = linkscoll.insert_many(links_to_save, ordered=False)
                except BulkWriteError as e:
                    print("  + WARNING: Could not store some resolved links in MongoDB because %s: %s" % (type(e), e.__dict__))
            #raise e
            todo, left = count_and_log(tweetscoll, batch_size, done=done, skip=skip)
            continue

        t = datetime.now().isoformat()
        print("  + [%s] STORING %s REDIRECTIONS IN MONGO" % (t, len(links_to_save)))
        if links_to_save:
            try:
                result = linkscoll.insert_many(links_to_save, ordered=False)
            except BulkWriteError as e:
                print("  + WARNING: Could not store some resolved links in MongoDB because %s: %s" % (type(e), e.__dict__))

        t = datetime.now().isoformat()
        print("  + [%s] UPDATING TWEETS LINKS IN MONGO" % t)
        tweets_already_done = []
        ids_done_in_batch = set()
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
            tweetscoll.update({'$or': [{'_id': tweetid}, {'retweet_id': tweetid}]}, {'$set': {'proper_links': gdlinks, 'links_to_resolve': False}}, upsert=False, multi=True)
            ids_done_in_batch.add(tweetid)

        # clear tweets potentially rediscovered
        if tweets_already_done:
            tweetscoll.update({"_id": {"$in": tweets_already_done}}, {"$set": {"links_to_resolve": False}}, upsert=False, multi=True)

        todo, left = count_and_log(tweetscoll, batch_size, done=done, skip=skip)

if __name__ == '__main__':
    resolve()
