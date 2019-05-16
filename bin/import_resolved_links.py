#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os, sys
import csv, json
from pymongo import MongoClient

verbose = True
if len(sys.argv) > 1 and "--quiet" in sys.argv:
    sys.argv.remove("--quiet")
    verbose = False

try:
    with open(os.path.join(os.path.dirname(__file__), '..', 'config.json')) as confile:
         conf = json.loads(confile.read())
except Exception as e:
    sys.stderr.write("ERROR: Impossible to read config.json: %s %s" % (type(e), e))
    exit(1)

try:
    #db = MongoClient(conf['mongo']['host'], conf['mongo']['port'])[conf['mongo']['db']]['links']
    db = MongoClient(conf['mongo']['host'], conf['mongo']['port'])["tweets-polarisation-2"]['links']
except Exception as e:
    sys.stderr.write("ERROR: Could not initiate connection to MongoDB: %s %s" % (type(e), e))
    exit(1)

try:
    with open(sys.argv[1]) as f:
        if verbose:
            count = 0
            for line in f:
                count += 1
            f.seek(0)
            import progressbar
            bar = progressbar.ProgressBar(max_value=count-1)
            iterator = bar(csv.reader(f, delimiter="\t"))
        else:
            iterator = csv.reader(f, delimiter="\t")
        iterator.next()
        for row in iterator:
            try:
                db.save({"_id": row[0], "real": row[1]})
            except Exception as e:
                print "- WARNING: Could not store resolved link %s -> %s because %s: %s" % (row[0], row[1], type(e), e)
except Exception as e:
    sys.stderr.write("ERROR: Could not open TSV file %s: %s %s" % (sys.argv[1], type(e), e))
    exit(1)
