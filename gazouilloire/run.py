#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys, time, urllib, json, re
from datetime import datetime
from httplib import BadStatusLine
from urllib2 import URLError
from ssl import SSLError
import socket
from pymongo import ASCENDING
try:
    from pymongo import MongoClient
except:
    from pymongo import Connection as MongoClient
from multiprocessing import Process, Queue
from twitter import Twitter, TwitterStream, OAuth, OAuth2, TwitterHTTPError
from tweets import prepare_tweets, get_timestamp
from pytz import timezone, all_timezones
from math import pi, sin, cos, acos

def log(typelog, text):
    sys.stderr.write("[%s] %s: %s\n" % (datetime.now(), typelog, text))

def depiler(pile, pile_extra, mongoconf, locale, debug=False):
    db = MongoClient(mongoconf['host'], mongoconf['port'])[mongoconf['db']]
    coll = db['tweets']
    while True:
        todo = []
        while not pile.empty():
            todo.append(pile.get())
        save = prepare_tweets(todo, locale)
        for t in save:
            if pile_extra and t["in_reply_to_status_id_str"]:
                if not coll.find_one({"_id": t["in_reply_to_status_id_str"]}):
                    pile_extra.put(t["in_reply_to_status_id_str"])
            tid = coll.save(t)
        if debug and save:
            log("DEBUG", "Saved %s tweets in MongoDB" % len(save))
        time.sleep(2)


def resolver(pile, pile_extra, twitterco, debug=False):
    while True:
        todo = []
        while not pile_extra.empty() and len(todo) < 100:
            todo.append(pile_extra.get())
        if todo:
            try:
                tweets = twitterco.statuses.lookup(_id=",".join(todo), _method="POST")
            except (TwitterHTTPError, BadStatusLine, URLError, SSLError) as e:
                log("WARNING", "API connection could not be established, retrying in 2 secs (%s: %s)" % (type(e), e))
                for t in todo:
                    pile_extra.put(t)
                time.sleep(10)
                continue
            if debug and tweets:
                log("DEBUG", "[conversations] +%d tweets" % len(tweets))
            for t in tweets:
                pile.put(dict(t))
        time.sleep(5)


real_min = lambda x, y: min(x, y) if x else y
date_to_time = lambda x: time.mktime(datetime.strptime(x[:16], "%Y-%m-%d %H:%M").timetuple())
re_andor = re.compile(r'(\([^)]+( OR [^)]+)*\) ?)+$')

def format_keyword(k):
    if k.startswith('@'):
        kutf = k.lstrip('@').encode('utf-8')
        return "from:%s OR to:%s OR @%s" % (kutf, kutf, kutf)
    if " AND " in k or " + " in k:
        k = "(%s)" % k.replace(" AND ", " ").replace(" + ", " ")
    return urllib.quote(k.encode('utf-8'), '')

def streamer(pile, streamco, keywords, timed_keywords, geocode, debug=False):
    while True:
        ts = time.time()
        extra_keywords = []

        # handle timed keywords and find first date when to stop
        end_time = None
        for keyw, planning in timed_keywords.items():
            for times in planning:
                t0 = date_to_time(times[0])
                t1 = date_to_time(times[1])
                if t0 < ts < t1:
                    extra_keywords.append(keyw)
                    end_time = real_min(end_time, t1)
                    break
                elif t0 > ts:
                    end_time = real_min(end_time, t0)
        log('INFO', 'Starting stream track until %s' % end_time)

        try:
            # TODO HANDLE USERS FOR STREAMING VIA GET IDS PUIS FOLLOW
            filter_keywords = [k.lstrip('@').strip().lower().encode('utf-8') for k in keywords + extra_keywords if " OR " not in k]
            for k in keywords + extra_keywords:
                if " OR " in k:
                    if re_andor.match(k):
                        ands = [o.split(' OR ') for o in k.strip('()').split(') (')]
                        combis = ands[0]
                        for ors in ands[1:]:
                            combis = ["%s %s" % (a, b) for a in combis for b in ors]
                        filter_keywords += combis
                    else:
                        log("WARNING", 'Ignoring keyword %s to streaming API, please use syntax with simple keywords separated by spaces or such as "(KEYW1 OR KEYW2) (KEYW3 OR KEYW4 OR KEYW5) (KEYW6)"' % k)
            if geocode:
                streamiter = streamco.statuses.filter(locations=geocode, filter_level='none', stall_warnings='true')
            else:
                streamiter = streamco.statuses.filter(track=",".join(filter_keywords), filter_level='none', stall_warnings='true')
        except (TwitterHTTPError, BadStatusLine, URLError, SSLError) as e:
            log("WARNING", "Stream connection could not be established, retrying in 2 secs (%s: %s)" % (type(e), e))
            time.sleep(2)
            continue

        try:
            for msg in streamiter:
                if end_time and end_time < time.time():
                    log("INFO", "Reached time to update list of keywords")
                    break
                if not msg:
                    continue
                if msg.get("disconnect") or msg.get("hangup"):
                    log("WARNING", "Stream connection lost: %s" % msg)
                    break
                if msg.get("timeout"):
                    continue
                if msg.get('text'):
                    if geocode:
                        tmptext = msg.get('text').lower().encode('utf-8')
                        keep = False
                        for k in filter_keywords:
                            if " " in k:
                                keep2 = True
                                for k2 in k.split(" "):
                                    if k2 not in tmptext:
                                        keep2 = False
                                        break
                                if keep2:
                                    keep = True
                                    break
                            elif k in tmptext:
                                keep = True
                                break
                        if not keep:
                            continue
                    pile.put(dict(msg))
                    if debug:
                        log("DEBUG", "[stream] +1 tweet")
                else:
                    log("INFO", "Got special data: %s" % str(msg))
        except (TwitterHTTPError, BadStatusLine, URLError, SSLError, socket.error) as e:
            log("WARNING", "Stream connection lost, reconnecting in a sec... (%s: %s)" % (type(e), e))

        if debug:
            log("DEBUG", "Stream stayed alive for %sh" % str((time.time()-ts)/3600))
        time.sleep(2)

chunkize = lambda a, n: [a[i:i+n] for i in xrange(0, len(a), n)]

def get_twitter_rates(conn):
    rate_limits = conn.application.rate_limit_status(resources="search")['resources']['search']['/search/tweets']
    return rate_limits['reset'], rate_limits['limit'], rate_limits['remaining']

def searcher(pile, searchco, keywords, timed_keywords, locale, geocode, debug=False):
    try:
        next_reset, max_per_reset, left = get_twitter_rates(searchco)
    except:
        log("ERROR", "Connecting to Twitter API via OAuth2 sign, could not get rate limits")
        sys.exit(1)

    queries = []
    fmtkeywords = []
    for k in keywords:
        if k.startswith("@"):
            queries.append(format_keyword(k))
        else:
            fmtkeywords.append(format_keyword(k))
    queries += [" OR ".join(a) for a in chunkize(fmtkeywords, 3)]
    timed_queries = {}
    queries_since_id = [0 for _ in queries + timed_keywords.items()]

    timegap = 1 + len(queries)
    while True:
        if time.time() > next_reset:
            try:
                next_reset, _, left = get_twitter_rates(searchco)
            except:
                next_reset += 15*60
                left = max_per_reset
        if not left:
            log("WARNING", "Stalling search queries with rate exceeded for the next %s seconds" % max(0, int(next_reset - time.time())))
            time.sleep(timegap + max(0, next_reset - time.time()))
            continue

        now = time.time()
        last_week = now - 60*60*24*7
        for keyw, planning in timed_keywords.items():
            keyw = format_keyword(keyw)
            timed_queries[keyw] = []
            for times in planning:
                t0 = date_to_time(times[0])
                t1 = date_to_time(times[1])
                if last_week < t0 < now or last_week < t1 < now:
                    timed_queries[keyw].append([t0, t1])

        if debug:
            log("DEBUG", "Starting search queries with %d remaining calls for the next %s seconds" % (left, int(next_reset - time.time())))

        for i, query in enumerate(queries + timed_queries.items()):

            planning = None
            if type(query) is tuple:
                planning = query[1]
                if not planning:
                    continue
                query = query[0]

            since = queries_since_id[i]
            max_id = 0
            while left:
                args = {'q': query, 'count': 100, 'include_entities': True, 'result_type': 'recent'}
                if geocode:
                    args['geocode'] = geocode
                if max_id:
                    args['max_id'] = str(max_id)
                if queries_since_id[i]:
                    args['since_id'] = str(queries_since_id[i])
                try:
                    res = searchco.search.tweets(**args)
                except (TwitterHTTPError, BadStatusLine, URLError, SSLError) as e:
                    log("WARNING", "Search connection could not be established, retrying in 2 secs (%s: %s)" % (type(e), e))
                    time.sleep(2)
                    continue
                tweets = res.get('statuses', [])
                left -= 1
                if not len(tweets):
                    break
                news = 0
                for tw in tweets:
                    tid = long(tw.get('id_str', str(tw.get('id', ''))))
                    if not tid:
                        continue
                    if since < tid:
                        since = tid + 1
                    if not max_id or max_id > tid:
                        max_id = tid - 1
                    if planning is not None:
                        ts = get_timestamp(tw, locale)
                        skip = True
                        for trang in planning:
                            if trang[0] < ts < trang[1]:
                                skip = False
                                break
                        if skip:
                            continue
                    pile.put(dict(tw))
                    news += 1
                if news == 0:
                    break
                if debug:
                    log("DEBUG", "[search] +%d tweets (%s)" % (news, query))
            queries_since_id[i] = since
        time.sleep(max(timegap, next_reset - time.time() - 2*left))

def generate_geoloc_strings(x1, y1, x2, y2):
    streamgeocode = "%s,%s,%s,%s" % (y1, x1, y2, x2)
    log('INFO', 'Stream Bounding box: %s/%s -> %s/%s' % (x1, y1, x2, y2))
    x = (x1 + x2) / 2
    y = (y1 + y2) / 2
    d = 6371 * acos(sin(x*pi/180) * sin(x1*pi/180) + cos(x*pi/180) * cos(x1*pi/180) * cos((y1-y)*pi/180))
    searchgeocode = "%s,%s,%.2fkm" % (x, y, d)
    log('INFO', 'Search Disk: %s/%s, %.2fkm' % (x, y, d))
    return streamgeocode, searchgeocode

if __name__=='__main__':
    try:
        with open('config.json') as confile:
            conf = json.loads(confile.read())
        oauth = OAuth(conf['twitter']['oauth_token'], conf['twitter']['oauth_secret'], conf['twitter']['key'], conf['twitter']['secret'])
        oauth2 = OAuth2(bearer_token=json.loads(Twitter(api_version=None, format="", secure=True, auth=OAuth2(conf['twitter']['key'], conf['twitter']['secret'])).oauth2.token(grant_type="client_credentials"))['access_token'])
        SearchConn = Twitter(domain="api.twitter.com", api_version="1.1", format="json", auth=oauth2, secure=True)
        ResConn = Twitter(domain="api.twitter.com", api_version="1.1", format="json", auth=oauth, secure=True)
        StreamConn = TwitterStream(domain="stream.twitter.com", api_version="1.1", auth=oauth, secure=True, block=False, timeout=10)
    except Exception as e:
        log('ERROR', 'Could not initiate connections to Twitter API: %s %s' % (type(e), e))
        sys.exit(1)
    try:
        locale = timezone(conf['timezone'])
    except:
        log('ERROR', "\t".join(all_timezones)+"\n\n")
        log('ERROR', 'Unknown timezone set in config.json: %s. Please choose one among the above ones.' % conf['timezone'])
        sys.exit(1)
    try:
        db = MongoClient(conf['mongo']['host'], conf['mongo']['port'])[conf['mongo']['db']]
        coll = db['tweets']
        coll.ensure_index([('_id', ASCENDING)], background=True)
        coll.ensure_index([('timestamp', ASCENDING)], background=True)
    except Exception as e:
        log('ERROR', 'Could not initiate connection to MongoDB: %s %s' % (type(e), e))
        sys.exit(1)
    streamgeocode = None
    searchgeocode = None
    if "geolocalisation" in conf:
        if type(conf["geolocalisation"]) == list:
            try:
                x1, y1, x2, y2 = conf["geolocalisation"]
                streamgeocode, searchgeocode = generate_geoloc_strings(x1, y1, x2, y2)
            except Exception as e:
                log('ERROR', 'geolocalisation is wrongly formatted, should be something such as ["Lat1", "Long1", "Lat2", "Long2"]')
                sys.exit(1)
        else:
            GeoConn = Twitter(domain="api.twitter.com", api_version="1.1", format="json", auth=oauth, secure=True)
            res = GeoConn.geo.search(query=conf["geolocalisation"].replace(" ", "+"), granularity=conf.get("geolocalisation_type", "admin"), max_results=1)
            try:
                place = res["result"]["places"][0]
                log('INFO', 'Limiting tweets search to place "%s" with id "%s"' % (place['full_name'], place['id']))
                y1, x1 = place["bounding_box"]['coordinates'][0][0]
                y2, x2 = place["bounding_box"]['coordinates'][0][2]
                streamgeocode, searchgeocode = generate_geoloc_strings(x1, y1, x2, y2)
            except Exception as e:
                log('ERROR', 'Could not find a place matching geolocalisation %s: %s %s' % (conf["geolocalisation"], type(e), e))
                sys.exit(1)
    grab_conversations = "grab_conversations" in conf and conf["grab_conversations"]
    pile = Queue()
    pile_extra = Queue() if grab_conversations else None
    depile = Process(target=depiler, args=(pile, pile_extra, conf['mongo'], locale, conf['debug']))
    depile.daemon = True
    depile.start()
    if grab_conversations:
        resolve = Process(target=resolver, args=(pile, pile_extra, ResConn, conf['debug']))
        resolve.daemon = True
        resolve.start()
    stream = Process(target=streamer, args=(pile, StreamConn, conf['keywords'], conf['time_limited_keywords'], streamgeocode, conf['debug']))
    stream.daemon = True
    stream.start()
    search = Process(target=searcher, args=(pile, SearchConn, conf['keywords'], conf['time_limited_keywords'], locale, searchgeocode, conf['debug']))
    search.start()
    depile.join()

