#/usr/bin/env python
# -*- coding: utf-8 -*-

import csv
from pymongo import MongoClient
from config import CSV_SOURCE, CSV_ENCODING, CSV_TWITTER_FIELD, MONGO_DATABASE, TWITTER
from gazouilloire.tweets import prepare_tweet, clean_user_entities
from gazouilloire.api_wrapper import TwitterWrapper

with open(CSV_SOURCE) as f:
    data = list(csv.DictReader(f, delimiter=';'))

api = TwitterWrapper(TWITTER)
db = MongoClient("localhost", 27017)[MONGO_DATABASE]

for i, row in enumerate(data):
    user = {}
    for k in row.keys():
        user[k.decode(CSV_ENCODING)] = row[k].decode(CSV_ENCODING).replace(u' ', ' ').strip()
    user['twitter'] = user[CSV_TWITTER_FIELD].lstrip('@').lower()
    print "- WORKING ON %s" % user['twitter'], user
    if db.users.find({'_id': user['twitter'], 'done': True}, limit=1).count():
        print "  ALREADY DONE!"
        continue
    user['done'] = False
    api_args = {'screen_name': user['twitter']}
    metas = api.call('users.show', api_args)
    clean_user_entities(metas)
    user.update(metas)
    db.users.update({'_id': user['twitter']}, {"$set": user}, upsert=True)
    if user['protected']:
        print "SKIPPING tweets for %s whose account is unfortunately protected" % user['twitter']
        continue
    api_args['count'] = 200
    api_args['contributor_details'] = 1
    api_args['include_rts'] = 1
    api_args['tweet_mode'] = "extended"
    tweets = api.call('statuses.user_timeline', api_args)
    while tweets:
        for tw in tweets:
            api_args['max_id'] = min(api_args.get('max_id', tw['id']), tw['id']-1)
            metas = prepare_tweet(tw)
            metas.pop('_id')
            tw.update(metas)
            for po in ['user', 'entities', 'extended_entities']:
                if po in tw:
                    tw.pop(po)
            db.tweets.update({'_id': tw['id']}, {"$set": tw}, upsert=True)
        print "...collected %s new tweets" % len(tweets)
        tweets = api.call('statuses.user_timeline', api_args)
    db.users.update({'_id': user['twitter']}, {"$set": {"done": True}})
