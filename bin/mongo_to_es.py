#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
from builtins import input, int, open, str
import os
import sys
import click
from datetime import datetime
from distutils.util import strtobool

import pymongo
from elasticsearch import Elasticsearch, helpers

from future import standard_library

sys.path.append(os.path.join(os.getcwd()))

from gazouilloire.database.elasticmanager import DB_MAPPINGS, format_tweet_fields

standard_library.install_aliases()
pymongo.unicode_decode_output = False

ES_TWEETS_MAPPINGS = DB_MAPPINGS['tweets_mapping']
ES_LINKS_MAPPINGS = DB_MAPPINGS['links_mapping']


@click.command()
@click.argument('mongo_db')
@click.argument('mongo_host', default='localhost')
@click.argument('mongo_port', default=27017)
@click.argument('es_index_name', default='')
@click.argument('es_host', default='localhost')
@click.argument('es_port', default=9200)
def migrate(mongo_host, mongo_port, mongo_db, es_host, es_port, es_index_name):
    if not es_index_name:
        es_index_name = mongo_db
    print("Initialising Mongo & ES clients...")
    MONGO_CLIENT = pymongo.MongoClient(
        'mongodb://%s:%s/' % (mongo_host, mongo_port))
    MONGO_DB = MONGO_CLIENT[mongo_db]
    ES_CLIENT = Elasticsearch('http://%s:%s' % (es_host, es_port))
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
        bulkload.append({
            '_id': tweet['_id'],
            '_source': format_tweet_fields(tweet)
        })

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
        links_bulkload.append({
            '_source': {
                "link_id": link['_id'],
                "real": link.get('real', None)
            }
        })


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
