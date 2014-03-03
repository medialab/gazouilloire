#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys, time, urllib, json
from httplib import BadStatusLine
from urllib2 import URLError
import pymongo
from multiprocessing import Process, Queue
from twitter import Twitter, TwitterStream, OAuth, OAuth2, TwitterHTTPError
from tweets import prepare_tweets

def depiler(pile, db, debug=False):
    while True:
        todo = []
        while not pile.empty():
            todo.append(pile.get())
        save = prepare_tweets(todo)
        ct = len(save)
        for t in save:
             tid = db.save(t)

def streamer(pile, streamco, keywords, debug=False):
    while True:
        sys.stderr.write('INFO: Starting stream track\n')
        try:
            streamiter = streamco.statuses.filter(track=",".join([k.lstrip('@').strip().lower() for k in keywords]).encode('utf-8'), filter_level='none', stall_warnings='true', block=True)
        except (TwitterHTTPError, BadStatusLine, URLError):
            time.sleep(2)
            continue
        for msg in streamiter:
            if not msg:
                continue
            if msg.get("disconnect") or msg.get("timeout") or msg.get("hangup"):
                sys.stderr.write("INFO: Stream connection lost: %s\n" % msg)
                break
            if msg.get('text'):
                pile.put(dict(msg))
                if debug:
                    sys.stderr.write("DEBUG: [stream] +1 tweet\n")
            else:
                sys.stderr.write("INFO: Got special data: %s\n" % str(msg))
        time.sleep(1)

chunkize = lambda a, n: [a[i:i+n] for i in xrange(0, len(a), n)]

def get_twitter_rates(conn):
    rate_limits = conn.application.rate_limit_status(resources="search")['resources']['search']['/search/tweets']
    return rate_limits['reset'], rate_limits['limit'], rate_limits['remaining']

def searcher(pile, searchco, keywords, debug=False):
    try:
        next_reset, max_per_reset, left = get_twitter_rates(searchco)
    except:
        sys.stderr.write("ERROR: Connecting to Twitter API via OAuth2 sign, could not get rate limits\n")
        sys.exit(1)
    keywords = [urllib.quote(k.encode('utf-8').replace('@', 'from:'),'') for k in keywords]
    queries = [" OR ".join(a) for a in chunkize(keywords, 4)]
    timegap = 1 + len(queries)
    queries_since_id = [0 for _ in queries]
    while True:
        if time.time() > next_reset:
            try:
                next_reset, _, left = get_twitter_rates(searchco)
            except:
                next_reset += 15*60
                left = max_per_reset
        if not left:
            sys.stderr.write("DEBUG: Stalling search queries with rate exceeded for the next %s seconds\n" % max(0, int(next_reset - time.time())))
            time.sleep(timegap + max(0, next_reset - time.time()))
            continue
        if debug:
            sys.stderr.write("INFO: Starting search queries with %d remaining calls for the next %s seconds\n" % (left, int(next_reset - time.time())))
        for i, query in enumerate(queries):
            since = queries_since_id[i]
            max_id = 0
            while left:
                args = {'q': query, 'count': 100, 'include_entities': True}
                if max_id:
                    args['max_id'] = str(max_id)
                if queries_since_id[i]:
                    args['since_id'] = str(queries_since_id[i])
                try:
                    res = searchco.search.tweets(**args)
                except (TwitterHTTPError, BadStatusLine, URLError):
                    time.sleep(2)
                    continue
                tweets = res.get('statuses', [])
                left -= 1
                if not len(tweets):
                    break
                if debug:
                    sys.stderr.write("DEBUG: [search] +%d tweets (%s)\n" % (len(tweets), query))
                for tw in tweets:
                    tid = long(tw.get('id_str', str(tw.get('id', ''))))
                    if not tid:
                        continue
                    if since < tid:
                        since = tid + 1
                    if not max_id or max_id > tid:
                        max_id = tid - 1
                    pile.put(dict(tw))
            queries_since_id[i] = since
        time.sleep(max(timegap, next_reset - time.time() - 2*left))

if __name__=='__main__':
    try:
        with open('config.json') as confile:
            conf = json.loads(confile.read())
        oauth = OAuth(conf['twitter']['oauth_token'], conf['twitter']['oauth_secret'], conf['twitter']['key'], conf['twitter']['secret'])
        oauth2 = OAuth2(bearer_token=json.loads(Twitter(api_version=None, format="", secure=True, auth=OAuth2(conf['twitter']['key'], conf['twitter']['secret'])).oauth2.token(grant_type="client_credentials"))['access_token'])
        SearchConn = Twitter(domain="api.twitter.com", api_version="1.1", format="json", auth=oauth2, secure=True)
        StreamConn = TwitterStream(domain="stream.twitter.com", api_version="1.1", auth=oauth, secure=True)
    except Exception as e:
        sys.stderr.write('ERROR: Could not initiate connections to Twitter API: %s %s\n' % (type(e), e))
        sys.exit(1)
    try:
        db = pymongo.Connection(conf['mongo']['host'], conf['mongo']['port'])[conf['mongo']['db']]
        coll = db['tweets']
        coll.ensure_index([('_id', pymongo.ASCENDING)], background=True)
        coll.ensure_index([('timestamp', pymongo.ASCENDING)], background=True)
    except:
        sys.stderr.write('ERROR: Could not initiate connection to MongoDB\n')
        sys.exit(1)

    pile = Queue()
    depile = Process(target=depiler, args=(pile, coll, conf['debug']))
    depile.daemon = True
    depile.start()
    stream = Process(target=streamer, args=(pile, StreamConn, conf['keywords'], conf['debug']))
    stream.daemon = True
    stream.start()
    search = Process(target=searcher, args=(pile, SearchConn, conf['keywords'], conf['debug']))
    search.start()
    depile.join()

