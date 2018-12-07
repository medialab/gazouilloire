#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
import csv
from pymongo import MongoClient
from config import CSV_SOURCE, CSV_ENCODING, CSV_TWITTER_FIELD, MONGO_DATABASE, TWITTER
from gazouilloire.tweets import prepare_tweet, clean_user_entities
from gazouilloire.api_wrapper import TwitterWrapper

with open(CSV_SOURCE) as f:
    data = list(csv.DictReader(f))

api = TwitterWrapper(TWITTER)
db = MongoClient("localhost", 27017)[MONGO_DATABASE]

for i, row in enumerate(data):
    user = {}
    for k in list(row.keys()):
        user[k.decode(CSV_ENCODING)] = row[k].decode(CSV_ENCODING).replace(u' ', ' ').strip()
    user['twitter'] = user[CSV_TWITTER_FIELD].lstrip('@').lower()
    print("- WORKING ON %s" % user['twitter'], user)
    if db.users.find({'_id': user['twitter'], 'done': True}, limit=1).count():
        print("  ALREADY DONE!")
        continue
    api_args = {'screen_name': user['twitter']}
    metas = api.call('users.show', api_args)
    clean_user_entities(metas)
    #if user['protected']:
    #    print "SKIPPING tweets for %s whose account is unfortunately protected" % user['twitter']
    #    continue
    print("  %s friends to get" % metas['friends_count'])
    api_args['count'] = 5000
    api_args['cursor'] = -1
    metas['friends'] = []
    while api_args['cursor']:
        res = api.call('friends.ids', api_args)
        metas['friends'] += res['ids']
        print("  -> query: %s, next: %s" % (len(metas['friends']), res['next_cursor']))
        api_args['cursor'] = res['next_cursor']
    user.update(metas)
    user['done'] = True
    db.users.update({'_id': user['twitter']}, {"$set": user}, upsert=True)

corpus_ids = {}
for u in db.users.find():
    corpus_ids[u['id']] = u['_id']

for u in db.users.find():
    follows = []
    for f in u['friends']:
        if f in corpus_ids:
            follows.append(corpus_ids[f])
    db.users.update({'_id': u['_id']}, {"$set": {"follows": follows}})
