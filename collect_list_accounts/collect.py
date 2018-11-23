from __future__ import print_function
# /usr/bin/env python
# -*- coding: utf-8 -*-
import os
import csv
import sys
import json
from pymongo import MongoClient, ASCENDING
from fake_useragent import UserAgent
from config import CSV_SOURCE, CSV_DELIMITER, CSV_ENCODING, CSV_TWITTER_FIELD, MONGO_DATABASE, TWITTER
from gazouilloire.run import resolve_url
sys.path.append(os.path.join(os.getcwd()))
from gazouilloire.tweets import prepare_tweet, clean_user_entities
from gazouilloire.api_wrapper import TwitterWrapper
from gazouilloire.database import db_manager

try:
    with open(os.path.join(os.getcwd(),'config.json')) as confile:
        db_conf = json.loads(confile.read())['database']
except Exception as e:
    print('ERROR', 'Could not open config.json: %s %s' % (type(e), e))
    sys.exit(1)

with open(os.path.join(os.getcwd(),'collect_list_accounts',CSV_SOURCE)) as f:
    data = list(csv.DictReader(f, delimiter=CSV_DELIMITER))

api = TwitterWrapper(TWITTER)
db = MongoClient("localhost", 27017)[MONGO_DATABASE]

linkscoll = db['links']
tweetscoll = db['tweets']
for f in ['retweet_id', 'in_reply_to_status_id_str', 'timestamp',
          'links_to_resolve', 'lang', 'user_lang', 'langs']:
    tweetscoll.ensure_index([(f, ASCENDING)], background=True)
tweetscoll.ensure_index([('links_to_resolve', ASCENDING), ('_id', ASCENDING)], background=True)

for i, row in enumerate(data):
    user = {}
    for k in list(row.keys()):
        user[k] = row[k].strip()
    user['twitter'] = user[CSV_TWITTER_FIELD].lstrip('@').lower()
    print("- WORKING ON %s" % user['twitter'], user)
    if db.users.find({'_id': user['twitter'], 'done': True}, limit=1).count():
        print("  ALREADY DONE!")
        continue
    user['done'] = False
    api_args = {'screen_name': user['twitter']}
    metas = api.call('users.show', api_args)
    if not metas:
        print("SKIPPING tweets for %s whose account unfortunately disappeared" %
              user['twitter'])
        continue
    clean_user_entities(metas)
    user.update(metas)
    user.pop('_id')
    db.users.update({'_id': user['twitter']}, {"$set": user}, upsert=True)
    if user['protected']:
        print("SKIPPING tweets for %s whose account is unfortunately protected" %
              user['twitter'])
        continue
    api_args['count'] = 200
    api_args['contributor_details'] = 1
    api_args['include_rts'] = 1
    api_args['tweet_mode'] = "extended"
    tweets = api.call('statuses.user_timeline', api_args)
    while tweets:
        for tw in tweets:
            api_args['max_id'] = min(api_args.get(
                'max_id', tw['id']), tw['id']-1)
            metas = prepare_tweet(tw)
            metas.pop('_id')
            tw.update(metas)
            for po in ['user', 'entities', 'extended_entities']:
                if po in tw:
                    tw.pop(po)
            db.tweets.update({'_id': tw['id']}, {"$set": tw}, upsert=True)
        print("...collected %s new tweets" % len(tweets))
        tweets = api.call('statuses.user_timeline', api_args)
    db.users.update({'_id': user['twitter']}, {"$set": {"done": True}})


# TODO: refacto all of this with gazouilloire/run.py

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

