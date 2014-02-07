#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys, time, re, urllib, json
import pymongo
from multiprocessing import Process, Queue
from twitter import Twitter, TwitterStream, OAuth, OAuth2
from tweets import prepare_tweets

def depiler(pile, db):
    while True:
        todo = []
        while not pile.empty():
            todo.append(pile.get())
        save = prepare_tweets(todo)
        for t in save:
            tid = db.save(t)
    #        sys.stderr.write("DEBUG: saved tweet %s\n" % tid)

def streamer(pile, streamco, keywords):
    while True:
        for msg in streamco.statuses.filter(track=",".join([k.lstrip('@').strip().lower() for k in keywords]).encode('utf-8'), filter_level='none', stall_warnings='true'):
            if not msg:
                continue
            if msg.get("disconnect") or msg.get("timeout") or msg.get("hangup"):
                sys.stderrr.write("Stream connection lost, restarting it: %s\n" % msg)
                break
            if msg.get('text'):
                pile.put(dict(msg))
            else:
                sys.stderrr.write("Got special data:\n")
                sys.stderrr.write(str(msg))

def searcher(pile, searchco, keywords):
    ts = 0
    since_id = 0
    query = " OR ".join([urllib.quote(k.encode('utf-8').replace('@', 'from:'),'') for k in conf['keywords']])
    while True:
        if time.time() - ts > 15*60:
            ts = time.time()
            left = 450
        if not left:
            time.sleep(ts + 15*60 - time.time())
            continue
        max_id = 0
        since = since_id
        while left:
            args = {'q': query, 'count': 100, 'include_entities': True}
            if max_id:
                args['max_id'] = str(max_id)
            if since_id:
                args['since_id'] = str(since_id)
            res = searchco.search.tweets(**args)
            metas = res.get('search_metadata', {})
            tweets = res.get('statuses', [])
            if not len(tweets):
                break
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
        time.sleep(30)

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
    depile = Process(target=depiler, args=((pile), coll,))
    depile.daemon = True
    depile.start()
    stream = Process(target=streamer, args=((pile), StreamConn, conf['keywords']))
    stream.daemon = True
    stream.start()
    search = Process(target=searcher, args=((pile), SearchConn, conf['keywords']))
    search.start()
    depile.join()

