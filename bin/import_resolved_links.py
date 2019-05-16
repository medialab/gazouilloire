#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os, sys
import csv, json
from pymongo import MongoClient

BULK_SIZE = 1000

verbose = True
if len(sys.argv) > 1 and "--quiet" in sys.argv:
    sys.argv.remove("--quiet")
    verbose = False

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
        bulk = []
        counter = 0
        for row in iterator:
            bulk.append({"_id": row[0], "real": row[1]})
            counter += 1
            if counter % BULK_SIZE == 0:
                try:
                    db.insert_many(bulk)
                except Exception as e:
                    sys.stderr.write("- WARNING: Could not insert bulk: %s: %s\n" % (type(e), e))
                    exit(1)
                bulk = []
                counter = 0
        if counter:
            try:
                db.insert_many(bulk)
            except Exception as e:
                sys.stderr.write("- WARNING: Could not insert bulk: %s: %s\n" % (type(e), e))
                exit(1)

except Exception as e:
    sys.stderr.write("ERROR: Could not open TSV file %s: %s %s" % (sys.argv[1], type(e), e))
    exit(1)
