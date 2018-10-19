# -*- coding: utf-8 -*-

import sys
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
    print(tweet["text"].replace("\n", ""))
