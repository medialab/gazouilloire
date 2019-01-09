import os
import sys
import requests

from flask import Flask, jsonify, request, make_response, send_from_directory
from flask_pymongo import PyMongo
from flask_cors import CORS, cross_origin
from elasticsearch import Elasticsearch

from datetime import datetime

ROOT_PATH = os.path.dirname(os.path.realpath(__file__))

PUBLIC_PATH = os.path.join(ROOT_PATH, 'public')

INDEX_NAME = "juliacage"
TWEETS = INDEX_NAME + "_tweets"

# Creating the Flask object
app = Flask(__name__)
CORS(app)
app.config['MONGO_URI'] = 'mongodb://127.0.0.1:27017/db2'
app.config['JSON_AS_ASCII'] = False
mongo = PyMongo(app)
es = Elasticsearch('http://localhost:9200')


def normalize_data(data, input_format="es"):
    if (input_format == "es"):
        tweets = []
        for row in data["hits"]["hits"]:
            tweet = row["_source"]
            tweets.append(tweet)
        return(tweets)


@app.errorhandler(404)
def not_found(error):
    """ error handler """
    return make_response(jsonify({'error': 'Not found'}), 404)


@app.route("/")
def hello():
    return send_from_directory(PUBLIC_PATH, 'index.html')


@app.route("/data")
def getTweetsMDB():
    tweets = [tweet for tweet in mongo.db.tweets.find({}, {'user_screen_name': 1, 'user_name': 1, 'user_description': 1, 'user_location': 1, 'user_profile_image_url': 1,
                                                           'timestamp': 1, 'favorite_count': 1, 'retweet_count': 1, 'text': 1, 'hashtags': 1, 'source': 1, 'medias': 1, 'proper_links': 1, 'langs': 1})]
    return make_response(jsonify(tweets))


@app.route("/elasticdata")
def getTweetsES():
    data = es.search(index=TWEETS, body={
                     "from": 0, "size": 100, "query": {"match_all": {}}})
    normalized_data = normalize_data(data)
    return make_response(jsonify(normalized_data))


@app.route("/timeevolution")
def getDayCount():
    days = [day for day in mongo.db.tweets.aggregate([{"$group": {"_id": {"$dateToString": {"format": "%Y-%m-%d", "date": {"$toDate": {"$multiply": [1000, "$timestamp"]}}}}, "date":{
                                                     "$first": {"$dateToString": {"format": "%Y-%m-%d", "date": {"$toDate": {"$multiply": [1000, "$timestamp"]}}}}}, "count": {"$sum": 1}}}, {"$sort": {'_id': 1}}])]
    return make_response(jsonify(days))


@app.route("/elastictimeevolution")
def getDayCountES():
    data = es.search(
        index=TWEETS,
        body={
            "query":
            {
                "match_all": {}
            },

            "aggs": {
                "tweetsbyday": {"date_histogram": {"field": "timestamp", "format": "yyyy-MM-dd", "interval": "day", "min_doc_count": 5, "order": {"_key": "asc"}}}
            }

        }

    )
    days = []
    for day in data['aggregations']['tweetsbyday']['buckets']:
        dayToAdd = {'date': day['key_as_string'], 'count': day['doc_count']}
        days.append(dayToAdd)
    #normalized_data = normalize_data(data)
    #data = es.search(index="tweets", body={"query": {"match_all": {}},"aggs":{"range":{"date_range":{"field":"timestamp","ranges": [{ "from": 1537578080,  "to": 1537837210, "key": "quarter_01" }]}}}})
    return make_response(jsonify(days))


@app.route("/userrepartition")
def getUserCount():
    users = [user for user in mongo.db.tweets.aggregate([{"$group": {"_id": "$user_screen_name", "count": {
                                                        "$sum": 1}}}, {"$sort": {'count': -1}}], allowDiskUse=True)]
    return make_response(jsonify(users))


@app.route("/elasticuserrepartition")
def getUserCountES():
    index = request.args.get('index')
    data = es.search(
        index=index + '_tweets',
        body={
            "query":
                {
                    "match_all": {}
                },
            "aggs":
                {
                    "users": {"terms": {"field": "user_screen_name", "order": {"_count": "desc"}}}
                }

        }
    )
    users = []
    for user in data['aggregations']['users']['buckets']:
        userToAdd = {'_id': user['key'],
                     'count': user['doc_count'], 'size': 10}
        users.append(userToAdd)
    return make_response(jsonify(users))


@app.route("/indexstats")
def getIndexStats():
    data = es.indices.stats(TWEETS)
    #normalized_data = normalize_data(data)
    return make_response(jsonify(data))


@app.route("/textanalysis")
def getSignificantTerms():
    query_string = request.args.get('query_string')
    include_retweets = request.args.get('include_retweets')
    size = request.args.get('size')
    if not include_retweets:
        data = es.search(
            index=TWEETS,
            body={
                "query": {
                    "bool": {
                        "must": [
                            {
                                "match": {
                                    "text": query_string
                                }
                            }
                        ],
                        "must_not": [
                            {
                                "exists": {
                                    "field": "retweet_id"
                                }
                            }
                        ]
                    }
                },
                "aggs": {
                    "products": {
                        "significant_terms": {
                            "field": "text",
                            "size": 30
                        }
                    }
                },
                "size": 0
            }
        )
    else:
        data = es.search(
            index=TWEETS,
            body={
                "query": {
                    "match": {
                        "text": query_string
                    }
                },
                "aggs": {
                    "products": {
                        "significant_terms": {
                            "field": "text",
                            "size": 30
                        }
                    }
                },
                "size": 0
            }
        )
    significant_terms = []
    for term in data['aggregations']['products']['buckets']:
        significant_terms.append(term)
    return make_response(jsonify(significant_terms))


if __name__ == '__main__':
    app.run(debug=True)
