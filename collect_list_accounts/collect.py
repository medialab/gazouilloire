#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
import os
import csv
import sys
import json
sys.path.append(os.path.join(os.getcwd()))
from pymongo import MongoClient
from config import CSV_SOURCE, CSV_DELIMITER, CSV_ENCODING, CSV_TWITTER_FIELD, MONGO_DATABASE, TWITTER
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
