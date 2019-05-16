#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os, sys
import json
from pymongo import MongoClient

try:
    with open(os.path.join(os.path.dirname(__file__), '..', 'config.json')) as confile:
         conf = json.loads(confile.read())
except Exception as e:
    sys.stderr.write("ERROR: Impossible to read config.json: %s %s\n" % (type(e), e))
    exit(1)

try:
    db = MongoClient(conf['mongo']['host'], conf['mongo']['port'])[conf['mongo']['db']]['links']
except Exception as e:
    sys.stderr.write("ERROR: Could not initiate connection to MongoDB: %s %s\n" % (type(e), e))
    exit(1)

verbose = True
if len(sys.argv) > 1 and "--quiet" in sys.argv:
    sys.argv.remove("--quiet")
    verbose = False

count = db.count()
iterator = db.find()
if verbose:
    import progressbar
    bar = progressbar.ProgressBar(max_value=count)
    iterator = bar(iterator)
print "url\tresolved"
for t in iterator:
    print ('%s\t%s' % (t["_id"], t["real"])).encode('utf-8')
