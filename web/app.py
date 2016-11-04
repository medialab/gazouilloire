#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os, json, sys, re, time
from datetime import date, timedelta, datetime
from pymongo import MongoClient
from tweets import export_csv
from flask import Flask, render_template, request, make_response

try:
    with open(os.path.join(os.path.dirname(__file__), '..', 'config.json')) as confile:
         conf = json.loads(confile.read())
except Exception as e:
    sys.stderr.write("ERROR: Impossible to read config.json: %s %s" % (type(e), e))
    exit(1)

try:
    mongodb = MongoClient(conf['mongo']['host'], conf['mongo']['port'])[conf['mongo']['db']]['tweets']
except Exception as e:
    sys.stderr.write("ERROR: Could not initiate connection to MongoDB: %s %s" % (type(e), e))
    exit(1)

app = Flask(__name__)

def init_args():
    return {
      'startdate': (date.today() - timedelta(days=7)).isoformat(),
      'enddate': date.today().isoformat(),
      'query': '',
      'filters': '',
      'errors': []
    }

@app.route("/")
def home():
    return render_template("home.html", **init_args())

mult_queries = re.compile("\s*;\s*")

@app.route("/download")
def download():
    args = init_args()
    for arg in ['startdate', 'enddate', 'query', 'filters']:
        args[arg] = request.args.get(arg)
        if args[arg] is None:
            args["errors"].append('Field "%s" missing' % arg)
            args[arg] = ''
        if arg.endswith('date'):
            try:
                d = datetime.strptime(args[arg], "%Y-%m-%d")
                if arg == "enddate":
                    d += timedelta(days=1)
                args[arg.replace("date", "time")] = time.mktime(d.timetuple())
            except Exception as e:
                args["errors"].append(u'Field "%s": « %s » is not a valid date (%s: %s)' % (arg, args[arg], type(e), e))
    if args.get("starttime", 0) > args.get("endtime", 0):
        args["errors"].append('Field "startdate" should be older than field "enddate"')
    if args["errors"]:
        return render_template("home.html", **args)
    query = {
      "$and": [
        {"timestamp": {"$gte": args["starttime"]}},
        {"timestamp": {"$lt": args["endtime"]}}
      ]
    }
    if args["query"]:
        for q in mult_queries.split(args["query"]):
            query["$and"].append({
              "text": re.compile(r"%s" % q, re.I)
            })
    if args["filters"]:
        for q in mult_queries.split(args["filters"]):
            query["$and"].append({
              "text": {"$not": re.compile(r"%s" % q, re.I)}
            })
    mongoiterator = mongodb.find(query, sort=[("_id", -1)])
    csv = export_csv(mongoiterator)
    res = make_response(csv)
    res.headers["Content-Type"] = "text/csv; charset=UTF-8"
    res.headers["Content-Disposition"] = "attachment; filename=tweets-%s-%s-%s.csv" % (args['startdate'], args['enddate'], args['query'])
    return res

if __name__ == "__main__":
    app.run(debug=True)
