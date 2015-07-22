#/usr/bin/env python
# -*- coding: utf-8 -*-

import csv, json
from time import time, sleep
from pymongo import MongoClient
from twitter import Twitter, OAuth2, TwitterHTTPError
from config import CSV_SOURCE, CSV_ENCODING, CSV_TWITTER_FIELD, MONGO_DATABASE, TWITTER
from gazouilloire.tweets import prepare_tweet

with open(CSV_SOURCE) as f:
    data = list(csv.DictReader(f, delimiter=';'))

oauth2 = OAuth2(bearer_token=json.loads(Twitter(api_version=None, format="", secure=True, auth=OAuth2(TWITTER['KEY'], TWITTER['SECRET'])).oauth2.token(grant_type="client_credentials"))['access_token'])
api = Twitter(auth=oauth2)

db = MongoClient("localhost", 27017)[MONGO_DATABASE]

def wrapper(route, args={}, tryouts=50):
    try:
        return route(**args)
    except TwitterHTTPError as e:
        routestr = '/'.join(route.uriparts[1:])
        if e.e.code == 429:
            reset = int(e.e.headers["x-rate-limit-reset"])
            sleeptime = int(reset - time() + 2)
            print "REACHED API LIMITS on %s %s, will wait for the next %ss" % (routestr, args, sleeptime)
            sleep(sleeptime)
            return wrapper(route, args, tryouts-1)
        elif tryouts:
            return wrapper(route, args, tryouts-1)
        else:
            print "ERROR after 50 tryouts for %s %s" % (routestr, args)

def cleaner(data):
    if 'entities' in data:
        for k in data['entities']:
            if 'urls' in data['entities'][k]:
                for url in data['entities'][k]['urls']:
                    try:
                        data[k] = data[k].replace(url['url'], url['expanded_url'])
                    except:
                        print "WARNING, couldn't process entity", url, k, data[k]
        data.pop('entities')
    if 'status' in data:
        data.pop('status')

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
    metas = wrapper(api.users.show, api_args)
    cleaner(metas)
    user.update(metas)
    db.users.update({'_id': user['twitter']}, {"$set": user}, upsert=True)
    if user['protected']:
        print "SKIPPING tweets for %s whose account is unfortunately protected" % user['twitter']
        continue
    api_args['count'] = 200
    api_args['contributor_details'] = 1
    api_args['include_rts'] = 1
    tweets = wrapper(api.statuses.user_timeline, api_args)
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
        tweets = wrapper(api.statuses.user_timeline, api_args)
    db.users.update({'_id': user['twitter']}, {"$set": {"done": True}})
