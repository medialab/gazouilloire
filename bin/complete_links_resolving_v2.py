#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import click
from pymongo import MongoClient, ASCENDING
from minet import multithreaded_resolve

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

def count_and_log(tweetscoll, batch_size, done=""):
    todo = list(tweetscoll.find({"links_to_resolve": True}, projection={"links": 1, "proper_links": 1, "retweet_id": 1}, limit=batch_size, sort=[("_id", 1)]))
    left = tweetscoll.count({"links_to_resolve": True})
    if done:
        done = "(+%s new redirections resolved out of %s)" % (done, len(todo))
    print("\n- RESOLVING LINKS: %s waiting %s\n" % (left, done))
    return todo, left

@click.command()
@click.argument('batch_size', default=BATCH_SIZE)
@click.argument('mongo_db', default=conf["mongo"]["db"])
@click.argument('mongo_host', default='localhost')
@click.argument('mongo_port', default=27017)
@click.option('--verbose/--silent', default=False)
def resolve(batch_size, mongo_db, mongo_host, mongo_port, verbose):
    linkscoll, tweetscoll = prepare_db(mongo_host, mongo_port, mongo_db)

    todo, left = count_and_log(tweetscoll, batch_size)
    while todo:
        done = 0
        batch_urls = list(set([l for t in todo if not t.get("proper_links", []) for l in t.get('links', [])]))
        alreadydone = {l["_id"]: l["real"] for l in linkscoll.find({"_id": {"$in": batch_urls}})}
        urls_to_clear = [u for u in batch_urls if u not in alreadydone]
        for res in multithreaded_resolve(urls_to_clear, threads=100, throttle=2, max_redirects=15):
            source = res.url
            status, target = res.stack[-1]
            if res.error:
                print("      ERROR %s on resolving %s: %s (last url: %s)" % (status, source, res.error, target))
                continue
            if verbose:
                print("          ", status, ":", source, "->", target)
            try:
                linkscoll.save({'_id': source, 'real': target})
                alreadydone[source] = target
                if source != target:
                    done += 1
            except Exception as e:
                print("  - WARNING: Could not store resolved link %s -> %s because %s: %s" % (source, target, type(e), e))

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
                continue
            tweetscoll.update({'$or': [{'_id': tweetid}, {'retweet_id': tweetid}]}, {'$set': {'proper_links': gdlinks, 'links_to_resolve': False}}, upsert=False, multi=True)
            ids_done_in_batch.add(tweetid)

        # clear tweets potentially rediscovered
        if tweets_already_done:
            tweetscoll.update({"_id": {"$in": tweets_already_done}}, {"$set": {"links_to_resolve": False}}, upsert=False, multi=True)

        todo, left = count_and_log(tweetscoll, batch_size, done=done)

if __name__ == '__main__':
    resolve()
