#/usr/bin/env python
# -*- coding: utf-8 -*-

import csv, json
from time import time, sleep
from pymongo import MongoClient
from twitter import Twitter, OAuth, OAuth2, TwitterHTTPError
from config import CSV_SOURCE, CSV_ENCODING, CSV_TWITTER_FIELD, MONGO_DATABASE, TWITTER
from gazouilloire.tweets import prepare_tweet

with open(CSV_SOURCE) as f:
    data = list(csv.DictReader(f))

oauth = OAuth(TWITTER['OAUTH_TOKEN'], TWITTER['OAUTH_SECRET'], TWITTER['KEY'], TWITTER['SECRET'])
oauth2 = OAuth2(bearer_token=json.loads(Twitter(api_version=None, format="", secure=True, auth=OAuth2(TWITTER['KEY'], TWITTER['SECRET'])).oauth2.token(grant_type="client_credentials"))['access_token'])
api = {
    'user': Twitter(auth=oauth),
    'app': Twitter(auth=oauth2)
}

db = MongoClient("localhost", 27017)[MONGO_DATABASE]

def wrapper(route, args={}, tryouts=50, apipath='user'):
    try:
        return api[apipath].__getattr__("/".join(route.split('.')))(**args)
    except TwitterHTTPError as e:
        if e.e.code == 429:
            if apipath == 'user':
                return wrapper(route, args, apipath='app')
            reset = int(e.e.headers["x-rate-limit-reset"])
            sleeptime = int(reset - time() + 2)
            print "REACHED API LIMITS on %s %s %s, will wait for the next %ss" % (route, apipath, args, sleeptime)
            sleep(sleeptime)
            return wrapper(route, args, tryouts-1)
        elif tryouts:
            return wrapper(route, args, tryouts-1, apipath)
        else:
            print "ERROR after 50 tryouts for %s %s %s" % (route, apipath, args)

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
    api_args = {'screen_name': user['twitter']}
    metas = wrapper('users.show', api_args)
    cleaner(metas)
    #if user['protected']:
    #    print "SKIPPING tweets for %s whose account is unfortunately protected" % user['twitter']
    #    continue
    print "  %s friends to get" % metas['friends_count']
    api_args['count'] = 5000
    api_args['cursor'] = -1
    metas['friends'] = []
    while api_args['cursor']:
        res = wrapper('friends.ids', api_args)
        metas['friends'] += res['ids']
        print "  -> query: %s, next: %s" % (len(metas['friends']), res['next_cursor'])
        api_args['cursor'] = res['next_cursor']
    user.update(metas)
    user['done'] = True
    db.users.update({'_id': user['twitter']}, {"$set": user}, upsert=True)
