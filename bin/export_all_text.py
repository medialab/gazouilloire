# -*- coding: utf-8 -*-

import sys, json, pymongo

with open('config.json') as confile:
    conf = json.loads(confile.read())

db = pymongo.Connection(conf['mongo']['host'], conf['mongo']['port'])[conf['mongo']['db']]['tweets']

for tweet in db.find():
    sys.stdout.write(tweet["text"].replace("\n", "").encode("utf-8")+"\n")


