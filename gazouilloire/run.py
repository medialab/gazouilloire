#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os, sys, time, urllib, json, re
from datetime import datetime
from httplib import BadStatusLine
from urllib2 import URLError
from ssl import SSLError
import socket
import requests
requests.packages.urllib3.disable_warnings()
from multiprocessing import Process, Queue, Event
import signal
from urlsresolver import resolve_url as resolve_redirects
from fake_useragent import UserAgent
from pymongo import ASCENDING
try:
    from pymongo import MongoClient
except:
    from pymongo import Connection as MongoClient
from twitter import Twitter, TwitterStream, OAuth, OAuth2, TwitterHTTPError
from tweets import prepare_tweets, get_timestamp
from pytz import timezone, all_timezones
from math import pi, sin, cos, acos

def log(typelog, text):
    try:
        sys.stderr.write("[%s] %s: %s\n" % (datetime.now(), typelog, text))
    except UnicodeEncodeError:
        sys.stderr.write("[%s] %s: %s\n" % (datetime.now(), typelog, text.encode('ascii', 'ignore')))

def depiler(pile, pile_deleted, pile_catchup, pile_links, pile_medias, mongoconf, locale, exit_event, debug=False):
    db = MongoClient(mongoconf['host'], mongoconf['port'])[mongoconf['db']]
    coll = db['tweets']
    while not exit_event.is_set() or not pile.empty() or not pile_deleted.empty():
        while not pile_deleted.empty():
            todelete = pile_deleted.get()
            coll.update(spec={'_id': todelete}, document={'$set': {'deleted': True}})

        todo = []
        while not pile.empty():
            todo.append(pile.get())
        save = prepare_tweets(todo, locale)
        for t in save:
            if pile_medias and t["medias"]:
                pile_medias.put(t)
            if pile_catchup and t["in_reply_to_status_id_str"]:
                if not coll.find_one({"_id": t["in_reply_to_status_id_str"]}):
                    pile_catchup.put(t["in_reply_to_status_id_str"])
            tid = coll.save(t)
            if pile_links and t["links"]:
                pile_links.put(t)
        if debug and save:
            log("DEBUG", "Saved %s tweets in MongoDB" % len(save))
        if not exit_event.is_set():
            time.sleep(2)
    log("INFO", "FINISHED depiler")

def download_media(tweet, media_id, media_url, medias_dir="medias"):
    subdir = os.path.join(medias_dir, media_id.split('_')[0][:-15])
    if not os.path.exists(subdir):
        os.makedirs(subdir)
    filepath = os.path.join(subdir, media_id)
    if os.path.exists(filepath):
        return 0
    try:
        r = requests.get(media_url, stream=True)
        with open(filepath, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)
        return 1
    except Exception as e:
        log("WARNING", "Could not download media %s for tweet %s (%s: %s)" % (media_url, tweet["url"], type(e), e))
        return 0

def downloader(pile_medias, medias_dir, exit_event, debug=False):
    while not exit_event.is_set() or not pile_medias.empty():
        todo = []
        while not pile_medias.empty():
            todo.append(pile_medias.get())
        if not todo:
            if not exit_event.is_set():
                time.sleep(2)
            continue
        done = 0
        for tweet in todo:
            for media_id, media_url in tweet["medias"]:
                done += download_media(tweet, media_id, media_url, medias_dir)
        if debug and done:
            log("DEBUG", "[medias] +%s files" % done)
    log("INFO", "FINISHED downloader")

def catchupper(pile, pile_catchup, twitterco, exit_event, debug=False):
    while not exit_event.is_set() or not pile_catchup.empty():
        todo = []
        while not pile_catchup.empty() and len(todo) < 100:
            todo.append(pile_catchup.get())
        if todo:
            try:
                tweets = twitterco.statuses.lookup(_id=",".join(todo), tweet_mode="extended", _method="POST")
            except (TwitterHTTPError, BadStatusLine, URLError, SSLError) as e:
                log("WARNING", "API connection could not be established, retrying in 2 secs (%s: %s)" % (type(e), e))
                for t in todo:
                    pile_catchup.put(t)
                if not exit_event.is_set():
                    time.sleep(10)
                continue
            if debug and tweets:
                log("DEBUG", "[conversations] +%d tweets" % len(tweets))
            for t in tweets:
                pile.put(dict(t))
        if not exit_event.is_set():
            time.sleep(5)
    log("INFO", "FINISHED catchupper")

re_clean_mobile_twitter = re.compile(r'^(https?://)mobile\.(twitter\.)')
def resolve_url(url, retries=5, user_agent=None):
    try:
        good = resolve_redirects(url, user_agent=user_agent.random, verify=False, timeout=5)
        return re_clean_mobile_twitter.sub(r'\1\2', good)
    except Exception as e:
        if retries:
            return resolve_url(url, retries-1, user_agent=user_agent)
        log("ERROR", "Could not resolve redirection for url %s (%s: %s)" % (url, type(e), e))
        return url

def resolver(pile_links, mongoconf, exit_event, debug=False):
    ua = UserAgent()
    ua.update()
    db = MongoClient(mongoconf['host'], mongoconf['port'])[mongoconf['db']]
    linkscoll = db['links']
    tweetscoll = db['tweets']
    while not exit_event.is_set() or not pile_links.empty():
        todo = []
        while not pile_links.empty() and len(todo) < 50:
            todo.append(pile_links.get())
        if not todo:
            if not exit_event.is_set():
                time.sleep(1)
            continue
        done = 0
        for tweet in todo:
            gdlinks = []
            for link in tweet["links"]:
                good = linkscoll.find_one({'_id': link})
                if good:
                    gdlinks.append(good['real'])
                    continue
                good = resolve_url(link, user_agent=ua)
                gdlinks.append(good)
                linkscoll.save({'_id': link, 'real': good})
                if link != good:
                    done += 1
            tweetscoll.update({'_id': tweet['_id']}, {'$set': {'proper_links': gdlinks}}, upsert=False)
        if debug and done:
            log("DEBUG", "[links] +%s links resolved (out of %s/%s)" % (done, len(todo), pile_links.qsize()))
    log("INFO", "FINISHED resolver")

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

def streamer(pile, pile_deleted, streamco, resco, keywords, timed_keywords, geocode, exit_event, debug=False):
    while not exit_event.is_set():
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
            # keywords tracked on stream
            filter_keywords = [k.strip().lower().encode('utf-8') for k in keywords + extra_keywords if " OR " not in k and not k.startswith('@')]
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

            # users followed on stream
            users = [k.lstrip('@').strip().lower().encode('utf-8') for k in keywords + extra_keywords if k.startswith('@')]
            keep_users = list(users)
            filter_users = []
            while users:
                for u in resco.users.lookup(screen_name=','.join(users[0:100]), include_entities=False):
                    filter_users.append(u['id_str'])
                users = users[100:]

            # prepare stream query arguments
            args = {'filter_level': 'none', 'stall_warnings': 'true'}
            if geocode:
                args['locations'] = geocode
            else:
                if filter_keywords:
                    args['track'] = ",".join(filter_keywords)
                if filter_users:
                    args['follow'] = ",".join(filter_users)
            streamiter = streamco.statuses.filter(**args)
        except KeyboardInterrupt:
            log("INFO", "closing streamer...")
            exit_event.set()
        except (TwitterHTTPError, BadStatusLine, URLError, SSLError) as e:
            log("WARNING", "Stream connection could not be established, retrying in 2 secs (%s: %s)" % (type(e), e))
            if not exit_event.is_set():
                time.sleep(2)
            continue

        try:
            for msg in streamiter:
                if exit_event.is_set():
                    break
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
                            tmpauthor = msg.get('screen_name').lower()
                            for u in keep_users:
                                if "@%s" % u in tmptext or u == tmpauthor:
                                    keep = True
                                    break
                        if not keep:
                            continue
                    pile.put(dict(msg))
                    if debug:
                        log("DEBUG", "[stream] +1 tweet")
                else:
                    if 'delete' in msg and 'status' in msg['delete'] and 'id_str' in msg['delete']['status']:
                        pile_deleted.put(msg['delete']['status']['id_str'])
                        if debug:
                            log("DEBUG", "[stream] -1 tweet (deleted by user)")
                    else:
                        log("INFO", "Got special data: %s" % str(msg))
        except (TwitterHTTPError, BadStatusLine, URLError, SSLError, socket.error) as e:
            log("WARNING", "Stream connection lost, reconnecting in a sec... (%s: %s)" % (type(e), e))
        except:
            log("INFO", "closing streamer...")
            exit_event.set()

        if debug:
            log("DEBUG", "Stream stayed alive for %sh" % str((time.time()-ts)/3600))
        if not exit_event.is_set():
            time.sleep(2)
    log("INFO", "FINISHED streamer")

chunkize = lambda a, n: [a[i:i+n] for i in xrange(0, len(a), n)]

def get_twitter_rates(conn):
    rate_limits = conn.application.rate_limit_status(resources="search")['resources']['search']['/search/tweets']
    return rate_limits['reset'], rate_limits['limit'], rate_limits['remaining']

def read_search_state():
    with open(".search_state.json") as f:
        return json.load(f)

def write_search_state(state):
    with open(".search_state.json", "w") as f:
        json.dump(state, f)

def searcher(pile, searchco, keywords, timed_keywords, locale, geocode, exit_event, debug=False):
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
    state = {q: 0 for q in queries + [format_keyword(k) for k in timed_keywords.keys()]}
    try:
        queries_since_id = read_search_state()
        assert queries_since_id and state.keys() == queries_since_id.keys()
        log("INFO", "Search queries restarting from previous state: %s" % queries_since_id)
    except:
        queries_since_id = state

    timegap = 1 + len(queries)
    while not exit_event.is_set():
      try:
        if time.time() > next_reset:
            try:
                next_reset, _, left = get_twitter_rates(searchco)
            except:
                next_reset += 15*60
                left = max_per_reset
        if not left:
            log("WARNING", "Stalling search queries with rate exceeded for the next %s seconds" % max(0, int(next_reset - time.time())))
            if not exit_event.is_set():
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

        for query in sorted(queries_since_id.keys()):

            try:
                planning = timed_queries[query]
                if not planning:
                    continue
            except KeyError:
                planning = None

            since = queries_since_id[query]
            max_id = 0
            while left and not exit_event.is_set():
                args = {'q': query, 'count': 100, 'include_entities': True, 'result_type': 'recent', 'tweet_mode': 'extended'}
                if geocode:
                    args['geocode'] = geocode
                if max_id:
                    args['max_id'] = str(max_id)
                if queries_since_id[query]:
                    args['since_id'] = str(queries_since_id[query])
                try:
                    res = searchco.search.tweets(**args)
                except (TwitterHTTPError, BadStatusLine, URLError, SSLError) as e:
                    log("WARNING", "Search connection could not be established, retrying in 2 secs (%s: %s)" % (type(e), e))
                    if not exit_event.is_set():
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
            queries_since_id[query] = since
            write_search_state(queries_since_id)
        if not exit_event.is_set():
            time.sleep(max(timegap, next_reset - time.time() - 2*left))
      except KeyboardInterrupt:
        log("INFO", "closing searcher...")
        exit_event.set()
    log("INFO", "FINISHED searcher")

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
    except Exception as e:
        log('ERROR', 'Could not open config.json: %s %s' % (type(e), e))
        sys.exit(1)
    try:
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
    if "geolocalisation" in conf and conf["geolocalisation"]:
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
    resolve_links = "resolve_redirected_links" in conf and conf["resolve_redirected_links"]
    dl_medias = "download_medias" in conf and conf["download_medias"]
    if dl_medias:
        medias_dir = conf.get("medias_directory", "medias")
        if not os.path.exists(medias_dir):
            os.makedirs(medias_dir)
    pile = Queue()
    pile_deleted = Queue()
    pile_catchup = Queue() if grab_conversations else None
    pile_links = Queue() if resolve_links else None
    pile_medias = Queue() if dl_medias else None
    default_handler = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    exit_event = Event()
    depile = Process(target=depiler, args=(pile, pile_deleted, pile_catchup, pile_links, pile_medias, conf['mongo'], locale, exit_event, conf['debug']))
    depile.daemon = True
    depile.start()
    if grab_conversations:
        catchup = Process(target=catchupper, args=(pile, pile_catchup, ResConn, exit_event, conf['debug']))
        catchup.daemon = True
        catchup.start()
    if resolve_links:
        resolve = Process(target=resolver, args=(pile_links, conf['mongo'], exit_event, conf['debug']))
        resolve.daemon = True
        resolve.start()
    if dl_medias:
        download = Process(target=downloader, args=(pile_medias, medias_dir, exit_event, conf['debug']))
        download.daemon = True
        download.start()
    signal.signal(signal.SIGINT, default_handler)
    stream = Process(target=streamer, args=(pile, pile_deleted, StreamConn, ResConn, conf['keywords'], conf['time_limited_keywords'], streamgeocode, exit_event, conf['debug']))
    stream.daemon = True
    stream.start()
    search = Process(target=searcher, args=(pile, SearchConn, conf['keywords'], conf['time_limited_keywords'], locale, searchgeocode, exit_event, conf['debug']))
    search.start()
    def stopper(*args):
        exit_event.set()
    signal.signal(signal.SIGTERM, stopper)
    try:
        depile.join()
    except KeyboardInterrupt:
        exit_event.set()
        depile.join()
