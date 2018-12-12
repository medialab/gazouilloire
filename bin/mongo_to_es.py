# -*- coding: utf-8 -*-
from distutils.util import strtobool
from datetime import datetime, timedelta
from pprint import pprint
from elasticsearch import helpers
from elasticsearch import Elasticsearch
import pymongo
import requests
import click
import json
import sys
import os
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import
from builtins import open
from builtins import input
from builtins import int
from builtins import str
from future import standard_library
standard_library.install_aliases()

try:
    with open(os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'gazouilloire', 'database', 'db_mappings.json'), 'r') as db_mappings:
        DB_MAPPINGS = json.loads(db_mappings.read())
except FileNotFoundError as e:
    print('ERROR -', 'Could not open db_mappings.json: %s %s' % (type(e), e))
    sys.exit(1)

pymongo.unicode_decode_output = False

ES_TWEETS_MAPPINGS = DB_MAPPINGS['tweets_mapping']
ES_LINKS_MAPPINGS = DB_MAPPINGS['links_mapping']


@click.command()
@click.argument('mongo_host')
@click.argument('mongo_port')
@click.argument('mongo_db')
@click.argument('es_host')
@click.argument('es_port')
@click.argument('es_index_name')
def migrate(mongo_host, mongo_port, mongo_db, es_host, es_port, es_index_name):
    print("Initialising Mongo & ES clients...")
    MONGO_CLIENT = pymongo.MongoClient(
        'mongodb://' + mongo_host + ':' + mongo_port + '/')
    MONGO_DB = MONGO_CLIENT[mongo_db]
    ES_CLIENT = Elasticsearch('http://' + es_host + ':' + es_port)
    ES_INDEX_NAME = es_index_name
    ES_LINKS_INDEX = ES_INDEX_NAME + '_links'
    ES_TWEETS_INDEX = ES_INDEX_NAME + '_tweets'

    if not ES_CLIENT.indices.exists(index=ES_TWEETS_INDEX):
        ES_CLIENT.indices.create(
            index=ES_TWEETS_INDEX, body=ES_TWEETS_MAPPINGS)
        existing_indices = []
    else:
        existing_indices = [ES_TWEETS_INDEX]

    if not ES_CLIENT.indices.exists(index=ES_LINKS_INDEX):
        ES_CLIENT.indices.create(
            index=ES_LINKS_INDEX, body=ES_LINKS_MAPPINGS)
    else:
        existing_indices.append(ES_LINKS_INDEX)
    if len(existing_indices) == 2:
        choice = strtobool(input(
            "WARNING: ES indices " + existing_indices[0] + " & " + existing_indices[1] + " already exist. Are you sure that you want to add tweets in these indices?\n(y/n) "))
        if not choice:
            sys.exit()
    elif len(existing_indices) == 1:
        choice = strtobool(input(
            "WARNING: ES index " + existing_indices[0] + " already exists. Are you sure that you want to add tweets in this index?\n(y/n) "))
        if not choice:
            sys.exit()
    startTime = datetime.now()
    i = 0
    bulkload = []
    print("Migrating database...")
    for tweet in MONGO_DB.tweets.find():
        i += 1
        try:
            coordinates = tweet['coordinates']['coordinates']
        except:
            coordinates = tweet.get('coordinates', None)
        load = {
            '_id': tweet['_id'],
            '_source': {
                "collected_at_timestamp": tweet.get('collected_at_timestamp', None),
                "collected_via_search": tweet.get('collected_via_search', None),
                "collected_via_stream": tweet.get('collected_via_stream', None),
                "coordinates": coordinates,
                "created_at": tweet.get('created_at', None),
                "deleted": False,
                "favorite_count": tweet.get('favorite_count', None),
                "hashtags": tweet.get('hashtags', None),
                "in_reply_to_screen_name": tweet.get('in_reply_to_screen_name', None),
                "in_reply_to_status_id_str": tweet.get('in_reply_to_status_id_str', None),
                "in_reply_to_user_id_str": tweet.get('in_reply_to_user_id_str', None),
                "lang": tweet.get('lang', None),
                "langs": tweet.get('langs', None),
                "links": tweet.get('links', None),
                "links_to_resolve": tweet.get('links_to_resolve', None),
                "medias": tweet.get('medias', None),
                "mentions_ids": tweet.get('mentions_ids', None),
                "mentions_names": tweet.get('mentions_names', None),
                "possibly_sensitive": tweet.get('possibly_sensitive', None),
                "proper_links": tweet.get('proper_links', None),
                "quoted_id": tweet.get('quoted_id', None),
                "quoted_timestamp": tweet.get('quoted_timestamp', None),
                "quoted_user": tweet.get('quoted_user', None),
                "quoted_user_id": tweet.get('quoted_user_id', None),
                "reply_count": tweet.get('reply_count', None),
                "retweet_count": tweet.get('retweet_count', None),
                "retweet_id": tweet.get('retweet_id', None),
                "retweet_timestamp": tweet.get('retweet_timestamp', None),
                "retweet_user": tweet.get('retweet_user', None),
                "retweet_user_id": tweet.get('retweet_user_id', None),
                "source": tweet.get('source', None),
                "text": tweet.get('text', None),
                "timestamp": tweet.get('timestamp', None),
                "truncated": tweet.get('truncated', None),
                "tweet_id": tweet.get('_id', None),
                "url": tweet.get('url', None),
                "user_created_at": tweet.get('user_created_at', None),
                "user_created_at_timestamp": tweet.get('user_created_at_timestamp', None),
                "user_description": tweet.get('user_description', None),
                "user_favourites": tweet.get('user_favourites', None),
                "user_followers": tweet.get('user_followers', None),
                "user_friends": tweet.get('user_friends', None),
                "user_id_str": tweet.get('user_id_str', None),
                "user_lang": tweet.get('user_lang', None),
                "user_listed": tweet.get('user_listed', None),
                "user_location": tweet.get('user_location', None),
                "user_name": tweet.get('user_name', None),
                "user_profile_image_url": tweet.get('user_profile_image_url', None),
                "user_profile_image_url_https": tweet.get('user_profile_image_url_https', None),
                "user_screen_name": tweet.get('user_screen_name', None),
                "user_statuses": tweet.get('user_statuses', None),
                "user_time_zone": tweet.get('user_time_zone', None),
                "user_url": tweet.get('user_url', None),
                "user_utc_offset": tweet.get('user_utc_offset', None),
                "user_verified": tweet.get('user_verified', None)}}

        bulkload.append(load)

        if i % 1800 == 0:
            helpers.bulk(ES_CLIENT, bulkload,
                         index=ES_TWEETS_INDEX, doc_type='tweet')
            bulkload = []
            print('  ' + str(i) + " tweets indexed.", end="\r")
    helpers.bulk(ES_CLIENT, bulkload, index=ES_TWEETS_INDEX, doc_type='tweet')
    print('  ' + str(i) + " tweets indexed.")
    i = 0
    links_bulkload = []
    for link in MONGO_DB.links.find():
        i += 1

        load = {
            '_source': {
                "link_id": link['_id'],
                "real": link.get('real', None)
            }}

        links_bulkload.append(load)

        if i % 1800 == 0:
            helpers.bulk(ES_CLIENT, links_bulkload,
                         index=ES_LINKS_INDEX, doc_type='link')
            links_bulkload = []
            print('  ' + str(i) + " links indexed.", end="\r")
    helpers.bulk(ES_CLIENT, links_bulkload,
                 index=ES_LINKS_INDEX, doc_type='link')
    print('  ' + str(i) + " links indexed.")
    print('Done (took', str((datetime.now() - startTime).total_seconds()) + ' seconds)')


if __name__ == '__main__':
    migrate()
