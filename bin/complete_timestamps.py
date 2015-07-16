# -*- coding: utf-8 -*-

import time, json, pymongo

with open('config.json') as confile:
    conf = json.loads(confile.read())

db = pymongo.Connection(conf['mongo']['host'], conf['mongo']['port'])[conf['mongo']['db']]['tweets']

for tweet in db.find():
    if "timestamp" not in tweet:
        tweet['timestamp'] = time.mktime(time.strptime(tweet['created_at'], '%a %b %d %H:%M:%S +0000 %Y'))
        db.save(tweet)



