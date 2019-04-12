# -*- coding: utf-8 -*-

import sys
import json
from gazouilloire.database.mongomanager import MongoManager

with open('config.json') as confile:
    conf = json.loads(confile.read())

db = MongoManager(conf['database']['host'], conf['database']['port'], conf['database']['db']).tweets

for tweet in db.find():
    print(tweet["text"].replace("\n", ""))
