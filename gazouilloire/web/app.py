#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os, json, sys, re, time
from datetime import date, timedelta, datetime
try:
    from pymongo import MongoClient
except:
    from pymongo import Connection as MongoClient
from export import export_csv, get_thread_ids_from_query
from flask import Flask, render_template, request, make_response
from flask_caching import Cache
from flask_compress import Compress

try:
    with open(os.path.join(os.path.dirname(__file__), '..', '..', 'config.json')) as confile:
         conf = json.loads(confile.read())
except Exception as e:
    sys.stderr.write("ERROR: Impossible to read config.json: %s %s" % (type(e), e))
    exit(1)
THREADS = conf.get('grab_conversations', False)
SELECTED_FIELD = conf.get('export', {}).get('selected_field', None)
EXTRA_FIELDS = conf.get('export', {}).get('extra_fields', [])

try:
    mongodb = MongoClient(conf['mongo']['host'], conf['mongo']['port'])[conf['mongo']['db']]['tweets']
except Exception as e:
    sys.stderr.write("ERROR: Could not initiate connection to MongoDB: %s %s" % (type(e), e))
    exit(1)

app = Flask(__name__)
Compress(app)
cache = Cache(app, config={'CACHE_TYPE': 'simple'})

def init_args():
    return {
      'startdate': (date.today() - timedelta(days=7)).isoformat(),
      'enddate': date.today().isoformat(),
      'query': '',
      'filters': '',
      'threads_option': THREADS,
      'include_threads': "checked" if THREADS else None,
      'selected_option': SELECTED_FIELD is not None,
      'selected': "checked" if SELECTED_FIELD else None
    }

@app.route("/")
@cache.cached(timeout=3600)
def home():
    return render_template("home.html", **init_args())

@app.route("/download")
def download():
    args = init_args()
    errors = []
    for arg in ['startdate', 'enddate', 'query', 'filters']:
        args[arg] = request.args.get(arg)
        if args[arg] is None:
            errors.append('Field "%s" missing' % arg)
            args[arg] = ''
        if arg.endswith('date'):
            try:
                d = datetime.strptime(args[arg], "%Y-%m-%d")
                if arg == "enddate":
                    d += timedelta(days=1)
                args[arg.replace("date", "time")] = time.mktime(d.timetuple())
            except Exception as e:
                errors.append(u'Field "%s": « %s » is not a valid date (%s: %s)' % (arg, args[arg], type(e), e))
    if THREADS:
        args['include_threads'] = request.args.get('threads')
    if SELECTED_FIELD:
        args['selected'] = request.args.get('selected')
    if args.get("starttime", 0) >= args.get("endtime", 0):
        errors.append('Field "startdate" should be older than field "enddate"')
    if errors:
        return make_response("\n".join(["error"] + errors))
    return queryData(args)

@cache.memoize(1800)
def queryData(args):
    query = {
      "$and": [
        {"timestamp": {"$gte": args["starttime"]}},
        {"timestamp": {"$lt": args["endtime"]}}
      ]
    }
    if args["query"]:
        for q in args["query"].split('|'):
            query["$and"].append({
              "text": re.compile(r"%s" % q, re.I)
            })
    if args["filters"]:
        for q in args["filters"].split('|'):
            query["$and"].append({
              "text": {"$not": re.compile(r"%s" % q, re.I)}
            })
    if SELECTED_FIELD and args['selected'] == 'checked':
        query["$and"].append({SELECTED_FIELD: True})
    if args["include_threads"]:
        ids = get_thread_ids_from_query(query, mongodb)
        query = {"_id": {"$in": ids}}
    mongoiterator = mongodb.find(query, sort=[("timestamp", 1)])
    csv = export_csv(mongoiterator, extra_fields=EXTRA_FIELDS)
    res = make_response(csv)
    res.headers["Content-Type"] = "text/csv; charset=UTF-8"
    res.headers["Content-Disposition"] = "attachment; filename=tweets-%s-%s-%s.csv" % (args['startdate'], args['enddate'], args['query'])
    return res

if __name__ == "__main__":
    app.run(debug=True)
