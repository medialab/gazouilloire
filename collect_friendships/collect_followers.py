#/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import csv
from collections import defaultdict
from pymongo import MongoClient
from config import MONGO_DATABASE, TWITTER
from gazouilloire.tweets import prepare_tweet, clean_user_entities
from gazouilloire.api_wrapper import TwitterWrapper

with open(sys.argv[1]) as f:
    source_users = [u["screen_name"].lstrip('@').lower() for u in csv.DictReader(f)]

api = TwitterWrapper(TWITTER)
db = MongoClient("localhost", 27017)[MONGO_DATABASE]

for u in source_users:
    print "- WORKING ON", u
    if db.users.find({'_id': u, 'done': True}, limit=1).count():
        print "  ALREADY DONE!"
        continue
    api_args = {'screen_name': u}
    user = api.call('users.show', api_args)
    clean_user_entities(user)
    user['done'] = False
    user['_id'] = u
    db.users.update({'_id': u}, {"$set": user}, upsert=True)

    print "  %s followers to get" % user['followers_count']
    api_args['count'] = 5000
    api_args['cursor'] = -1
    user['followers'] = []
    while api_args['cursor']:
        res = api.call('followers.ids', api_args)
        user['followers'] += res['ids']
        print "  -> query: %s, next: %s" % (len(user['followers']), res['next_cursor'])
        api_args['cursor'] = res['next_cursor']
    user['done'] = True
    db.users.update({'_id': u}, {"$set": user}, upsert=True)

users = defaultdict(dict)
for u in db.users.find():
    for f in u["followers"]:
        users[str(f)]["follows_%s" % u["screen_name"]] = True

followers_ids = users.keys()
n_followers = len(followers_ids)
print " => %s unique followers found, collecting their metas..." % n_followers

ct = 0
while ct < n_followers:
    batch = followers_ids[ct:ct+100]
    print " - collecting followers #%s -> %s" % (ct, min(n_followers, ct+100))
    for u in api.call('users.lookup', {"user_id": ",".join(batch)}):
        clean_user_entities(u)
        users[u["id_str"]].update(u)
        users[u["id_str"]]["_id"] = u["screen_name"].lower()
        db.users.update({'_id': u["screen_name"].lower()}, {"$set": users[u["id_str"]]}, upsert=True)
    ct = ct + 100

