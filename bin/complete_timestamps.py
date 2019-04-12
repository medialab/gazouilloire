# -*- coding: utf-8 -*-

import time
import json
from gazouilloire.database.mongomanager import MongoManager

with open('config.json') as confile:
    conf = json.loads(confile.read())

db = MongoManager(conf['database']['host'], conf['database']['port'], conf['database']['db']).tweets

for tweet in db.find():
    if "timestamp" not in tweet:
        tweet['timestamp'] = time.mktime(time.strptime(
            tweet['created_at'], '%a %b %d %H:%M:%S +0000 %Y'))
        db.save(tweet)
