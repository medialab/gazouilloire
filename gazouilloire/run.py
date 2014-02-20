#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys, time, re, urllib, json
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
        for msg in streamco.statuses.filter(track=",".join([k.lstrip('@').strip().lower() for k in keywords]).encode('utf-8'), filter_level='none', stall_warnings='true', block=False):
            if not msg:
                continue
            if msg.get("disconnect") or msg.get("timeout") or msg.get("hangup"):
                sys.stderr.write("INFO: Stream connection lost: %s\n" % msg)
                break
            if msg.get('text'):
                pile.put(dict(msg))
                if debug:
                    sys.stderr.write("DEBUG: [stream] +1 tweet\n" % ct)
            else:
                sys.stderr.write("INFO: Got special data:\n")
                sys.stderr.write(str(msg)+"\n")
        time.sleep(1)

def searcher(pile, searchco, keywords, debug=False):
    since_id = 0
    try:
        rate_limits = searchco.application.rate_limit_status(resources="search")['resources']['search']['/search/tweets']
        next_reset = rate_limits['reset']
        max_per_reset = rate_limits['limit']
        left = rate_limits['remaining']
    except:
        sys.stderr.write("ERROR Connecting to Twitter API via OAuth2 sign, could not get rate limits\n")
        sys.exit(1)
    query = " OR ".join([urllib.quote(k.encode('utf-8').replace('@', 'from:'),'') for k in keywords])
    while True:
        if time.time() > next_reset:
            next_reset += 15*60
            left = max_per_reset
        if not left:
            time.sleep(5 + max(0, next_reset - time.time()))
            if debug:
                sys.stderr.write("DEBUG: Stalling search queries with rate exceeded for the next %s seconds\n" % max(0, next_reset - time.time()))
            continue
        sys.stderr.write("INFO: Starting search queries with %d remaining calls for the next %s seconds\n" % (left, next_reset - time.time()))
        max_id = 0
        since = since_id
        while left:
            args = {'q': query, 'count': 100, 'include_entities': True}
            if max_id:
                args['max_id'] = str(max_id)
            if since_id:
                args['since_id'] = str(since_id)
            try:
                res = searchco.search.tweets(**args)
            except TwitterHTTPError:
                time.sleep(2)
                continue
            tweets = res.get('statuses', [])
            left -= 1
            if not len(tweets):
                break
            if debug:
                sys.stderr.write("DEBUG: [search] +%d tweets\n" % len(tweets))
            for tw in tweets:
                tid = long(tw.get('id_str', str(tw.get('id', ''))))
                if not tid:
                    continue
                if since < tid:
                    since = tid + 1
                if not max_id or max_id > tid:
                    max_id = tid - 1
                pile.put(dict(tw))
        since_id = since
        time.sleep(5 + max(0, next_reset - time.time() - 4*left))

if __name__=='__main__':
    try:
        with open('config.json') as confile:
            conf = json.loads(confile.read())
        oauth = OAuth(conf['twitter']['oauth_token'], conf['twitter']['oauth_secret'], conf['twitter']['key'], conf['twitter']['secret'])
        oauth2 = OAuth2(bearer_token=json.loads(Twitter(api_version=None, format="", secure=True, auth=OAuth2(conf['twitter']['key'], conf['twitter']['secret'])).oauth2.token(grant_type="client_credentials"))['access_token'])
        SearchConn = Twitter(domain="api.twitter.com", api_version="1.1", format="json", auth=oauth2, secure=True)
        StreamConn = TwitterStream(domain="stream.twitter.com", api_version="1.1", auth=oauth, secure=True)
    except Exception as e:
        print type(e), e
        sys.stderr.write('ERROR: Could not initiate connections to Twitter API\n')
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
    depile = Process(target=depiler, args=((pile), coll, conf['debug']))
    depile.daemon = True
    depile.start()
    stream = Process(target=streamer, args=((pile), StreamConn, conf['keywords'], conf['debug']))
    stream.daemon = True
    stream.start()
    search = Process(target=searcher, args=((pile), SearchConn, conf['keywords'], conf['debug']))
    search.start()
    depile.join()

