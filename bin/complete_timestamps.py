# -*- coding: utf-8 -*-

import time
import json
try:
    from pymongo import MongoClient
except ImportError:
    from pymongo.connection import Connection as MongoClient

with open('config.json') as confile:
    conf = json.loads(confile.read())

db = MongoClient(conf['mongo']['host'], conf['mongo']['port'])[
    conf['mongo']['db']]['tweets']

for tweet in db.find():
    if "timestamp" not in tweet:
        tweet['timestamp'] = time.mktime(time.strptime(
            tweet['created_at'], '%a %b %d %H:%M:%S +0000 %Y'))
        db.save(tweet)
