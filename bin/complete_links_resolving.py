#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
from gazouilloire.database.mongomanager import MongoManager, ASCENDING
from fake_useragent import UserAgent

from gazouilloire.run import resolve_url

with open('config.json') as confile:
    conf = json.loads(confile.read())

db = MongoManager(conf['database']['host'], conf['database']['port'], conf['database']['db']).db

# TODO: refacto all of this with gazouilloire/run.py

linkscoll = db['links']
tweetscoll = db['tweets']
for f in ['retweet_id', 'in_reply_to_status_id_str', 'timestamp',
          'links_to_resolve', 'lang', 'user_lang', 'langs']:
    tweetscoll.ensure_index([(f, ASCENDING)], background=True)
tweetscoll.ensure_index([('links_to_resolve', ASCENDING), ('_id', ASCENDING)], background=True)

ua = UserAgent()
ua.update()
todo = list(tweetscoll.find({"links_to_resolve": True}, projection={"links": 1, "proper_links": 1, "retweet_id": 1}, limit=600, sort=[("_id", 1)]))
left = tweetscoll.count({"links_to_resolve": True})
print "\n\n- STARTING LINKS RESOLVING: %s waiting\n\n" % left
while todo:
    done = 0
    urlstoclear = list(set([l for t in todo if not t.get("proper_links", []) for l in t.get('links', [])]))
    alreadydone = {l["_id"]: l["real"] for l in linkscoll.find({"_id": {"$in": urlstoclear}})}
    tweetsdone = []
    batchidsdone = set()
    for tweet in todo:
        if tweet.get("proper_links", []):
            tweetsdone.append(tweet["_id"])
            continue
        tweetid = tweet.get('retweet_id') or tweet['_id']
        if tweetid in batchidsdone:
            continue
        gdlinks = []
        for link in tweet.get("links", []):
            if link in alreadydone:
                gdlinks.append(alreadydone[link])
                continue
            print "          ", link
            good = resolve_url(link, user_agent=ua)
            gdlinks.append(good)
            try:
                linkscoll.save({'_id': link, 'real': good})
            except Exception as e:
                print "- WARNING: Could not store resolved link %s -> %s because %s: %s" % (link, good, type(e), e)
            if link != good:
                done += 1
        tweetscoll.update({'$or': [{'_id': tweetid}, {'retweet_id': tweetid}]}, {'$set': {'proper_links': gdlinks, 'links_to_resolve': False}}, upsert=False, multi=True)
        batchidsdone.add(tweetid)
    # clear tweets potentially rediscovered
    if tweetsdone:
        tweetscoll.update({"_id": {"$in": tweetsdone}}, {"$set": {"links_to_resolve": False}}, upsert=False, multi=True)
    if done:
        left = tweetscoll.count({"links_to_resolve": True})
        print "- [LINKS RESOLVING] +%s new redirection resolved out of %s links (%s waiting)" % (done, len(todo), left)
    todo = list(tweetscoll.find({"links_to_resolve": True}, projection={"links": 1, "proper_links": 1, "retweet_id": 1}, limit=600, sort=[("_id", 1)]))

