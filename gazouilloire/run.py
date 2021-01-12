#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import unicode_literals
from __future__ import division
from past.utils import old_div
from builtins import int
from builtins import str
from builtins import bytes
from builtins import range
import os, sys, time, json, re
from datetime import datetime
try:
    from httplib import BadStatusLine
    from urllib2 import URLError
    from urllib import quote
except ImportError:
    from http.client import BadStatusLine
    from urllib.error import URLError
    from urllib.parse import quote

from ssl import SSLError
import socket
import requests
requests.packages.urllib3.disable_warnings()
from multiprocessing import Process, Queue, Event
import signal
from twitter import Twitter, TwitterStream, OAuth, OAuth2, TwitterHTTPError
from pytz import timezone, all_timezones
from math import pi, sin, cos, acos

from gazouilloire.tweets import prepare_tweet, prepare_tweets
from gazouilloire.database.elasticmanager import ElasticManager, prepare_db
from elasticsearch import helpers
from gazouilloire.url_resolve import resolve_loop, count_and_log
from gazouilloire.config_format import load_conf, log

RESOLVER_BATCH_SIZE = 200


def get_timestamp(time, locale):
    tim = datetime.strptime(time, '%a %b %d %H:%M:%S +0000 %Y')
    if locale:
        utc_date = timezone('UTC').localize(tim)
        locale_date = utc_date.astimezone(locale)
        return locale_date.timestamp()
    return tim.timestamp()


def breakable_sleep(delay, exit_event):
    t = time.time() + delay
    while time.time() < t and not exit_event.is_set():
        time.sleep(1)

def depiler(pile, pile_deleted, pile_catchup, pile_medias, db_conf, locale, exit_event):
    db = ElasticManager(**db_conf)
    while not exit_event.is_set() or not pile.empty() or not pile_deleted.empty():
        log.info("Pile length: " + str(pile.qsize()))
        while not pile_deleted.empty():
            todelete = pile_deleted.get()
            db.set_deleted(todelete)
        todo = []
        while not pile.empty():
            todo.append(pile.get())
        tweets_bulk = []
        for t in prepare_tweets(todo, locale):
            if pile_medias and t["media_files"]:
                pile_medias.put(t)
            if pile_catchup and t["to_tweetid"]:
                if not db.find_tweet(t["to_tweetid"]):
                    pile_catchup.put(t["to_tweetid"])
            tweets_bulk.append(t)

        helpers.bulk(db.client, actions=db.prepare_indexing_tweets(tweets_bulk))
        if tweets_bulk:
            log.debug("Saved %s tweets in database" % len(tweets_bulk))
        breakable_sleep(2, exit_event)
    log.info("FINISHED depiler")

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
        log.warning("Could not download media %s for tweet %s (%s: %s)" % (media_url, tweet["url"], type(e), e))
        return 0


def downloader(pile_medias, medias_dir, media_types, exit_event):
    while not exit_event.is_set() or not pile_medias.empty():
        todo = []
        while not pile_medias.empty():
            todo.append(pile_medias.get())
        if not todo:
            breakable_sleep(2, exit_event)
            continue
        done = 0
        for tweet in todo:
            for enum, media_id in enumerate(tweet["media_files"]):
                if tweet["media_types"][enum] in media_types:
                    done += download_media(tweet, media_id, tweet["media_urls"][enum], medias_dir)
        if done:
            log.debug("[medias] +%s files" % done)
    log.info("FINISHED downloader")

# TODO
# - mark as deleted tweet_ids missing from request result
def catchupper(pile, pile_catchup, twitterco, exit_event):
    while not exit_event.is_set() or not pile_catchup.empty():
        todo = []
        while not pile_catchup.empty() and len(todo) < 100:
            todo.append(pile_catchup.get())
        if todo:
            try:
                tweets = twitterco.statuses.lookup(_id=",".join(todo), tweet_mode="extended", _method="POST")
            except (TwitterHTTPError, BadStatusLine, URLError, SSLError) as e:
                log.warning("API connection could not be established, retrying in 10 secs (%s: %s)" % (type(e), e))
                for t in todo:
                    pile_catchup.put(t)
                breakable_sleep(10, exit_event)
                continue
            if tweets:
                log.debug("[conversations] +%d tweets" % len(tweets))
            for t in tweets:
                t["gazouilloire_source"] = "thread"
                pile.put(dict(t))
        breakable_sleep(5, exit_event)
    log.info("FINISHED catchupper")

def resolver(batch_size, db_conf, exit_event, verbose=False):
    db = prepare_db(**db_conf)
    skip = 0
    done = 0
    while not exit_event.is_set():
        todo = count_and_log(db, batch_size, done=done, skip=skip)
        done, skip = resolve_loop(batch_size, db, todo, skip, verbose=verbose)
        time.sleep(30)
    log.info("FINISHED resolver")

real_min = lambda x, y: min(x, y) if x else y
date_to_time = lambda x: time.mktime(datetime.strptime(x[:16], "%Y-%m-%d %H:%M").timetuple())
re_andor = re.compile(r'(\([^)]+( OR [^)]+)*\) ?)+$')

def format_keyword(k):
    if k.startswith('@'):
        k = k.lstrip('@')
        return "from:%s OR to:%s OR @%s" % (k, k, k)
    if " AND " in k or " + " in k:
        k = "(%s)" % k.replace(" AND ", " ").replace(" + ", " ")
    return quote(k.encode('utf-8'), '')

def format_url_queries(urlpieces):
    return [format_url_query(q) for q in urlpieces]

re_split_url_pieces = re.compile(r'[^a-z0-9]+', re.I)
def format_url_query(urlquery):
    return " ".join([k for k in re_split_url_pieces.split(urlquery) if k.strip()])

def streamer(pile, pile_deleted, streamco, resco, keywords, urlpieces, timed_keywords, locale, language, geocode, exit_event):
    # Stream parameters reference: https://developer.twitter.com/en/docs/tweets/filter-realtime/guides/basic-stream-parameters
    # Stream operators reference: https://developer.twitter.com/en/docs/tweets/rules-and-filtering/overview/standard-operators.html
    # Stream special messages reference: https://developer.twitter.com/en/docs/tweets/filter-realtime/guides/streaming-message-types
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
        log.info('Starting stream track until %s' % end_time)

        try:
            # keywords tracked on stream
            query_keywords = [k.strip().lower() for k in keywords + format_url_queries(urlpieces) + extra_keywords if " OR " not in k and not k.startswith('@')]
            filter_keywords = [k.strip().lower() for k in keywords + urlpieces + extra_keywords if " OR " not in k and not k.startswith('@')]
            for k in keywords + extra_keywords:
                if " OR " in k:
                    if re_andor.match(k):
                        ands = [o.split(' OR ') for o in k.strip('()').split(') (')]
                        combis = ands[0]
                        for ors in ands[1:]:
                            combis = ["%s %s" % (a, b) for a in combis for b in ors]
                        query_keywords += combis
                        filter_keywords += combis
                    else:
                        log.warning('Ignoring keyword %s to streaming API, please use syntax with simple keywords separated by spaces or such as "(KEYW1 OR KEYW2) (KEYW3 OR KEYW4 OR KEYW5) (KEYW6)"' % k)

            # users followed on stream
            users = [k.lstrip('@').strip().lower() for k in keywords + extra_keywords if k.startswith('@')]
            keep_users = list(users)
            query_users = []
            while users:
                for u in resco.users.lookup(screen_name=','.join(users[0:100]), include_entities=False):
                    query_users.append(u['id_str'])
                users = users[100:]

            # prepare stream query arguments
            args = {'filter_level': 'none', 'stall_warnings': 'true'}
            if language:
                args['language'] = language
            if geocode:
                args['locations'] = geocode
            else:
                if query_keywords:
                    args['track'] = ",".join(query_keywords)
                if query_users:
                    args['follow'] = ",".join(query_users)
            log.debug("Calling stream with args %s" % args)
            streamiter = streamco.statuses.filter(**args)
        except KeyboardInterrupt:
            log.info("closing streamer...")
            exit_event.set()
        except (TwitterHTTPError, BadStatusLine, URLError, SSLError) as e:
            log.warning("Stream connection could not be established, retrying in 2 secs (%s: %s)" % (type(e), e))
            breakable_sleep(2, exit_event)
            continue

        try:
            for msg in streamiter:
                if exit_event.is_set():
                    break
                if end_time and end_time < time.time():
                    log.info("Reached time to update list of keywords")
                    break
                if not msg:
                    continue
                if msg.get("disconnect") or msg.get("hangup"):
                    log.warning("Stream connection lost: %s" % msg)
                    break
                if msg.get("timeout"):
                    continue
                if msg.get('id_str'):
                    msg["gazouilloire_source"] = "stream"
                    for tweet in prepare_tweet(msg, locale=locale):
                        if geocode or (urlpieces and not keywords):
                            tmptext = tweet["text"].lower()
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
                            if not keep and keep_users:
                                tmpauthor = tweet['user_screen_name'].lower()
                                for u in keep_users:
                                    if "@%s" % u in tmptext or u == tmpauthor:
                                        keep = True
                                        break
                            if not keep:
                                continue
                        pile.put(tweet)
                        log.debug("[stream] +1 tweet")
                else:
                    if 'delete' in msg and 'status' in msg['delete'] and 'id_str' in msg['delete']['status']:
                        pile_deleted.put(msg['delete']['status']['id_str'])
                        log.debug("[stream] -1 tweet (deleted by user)")
                    else:
                        log.info("Got special data: %s" % str(msg))
        except (TwitterHTTPError, BadStatusLine, URLError, SSLError, socket.error) as e:
            log.warning("Stream connection lost, reconnecting in a sec... (%s: %s)" % (type(e), e))
        except (Exception, KeyboardInterrupt) as e:
            log.info("closing streamer (%s: %s)..." % (type(e), e))
            exit_event.set()

        log.debug("Stream stayed alive for %sh" % str(old_div((time.time()-ts),3600)))
        breakable_sleep(2, exit_event)
    log.info("FINISHED streamer")

chunkize = lambda a, n: [a[i:i+n] for i in range(0, len(a), n)]

def get_twitter_rates(conn, conn2, retry=0):
    try:
        rate_limits = conn.application.rate_limit_status(resources="search")['resources']['search']['/search/tweets']
        rate_limits2 = conn2.application.rate_limit_status(resources="search")['resources']['search']['/search/tweets']
    except URLError as e:
        if retry:
            time.sleep(1)
            return get_twitter_rates(conn, conn2, retry=retry-1)
        raise e
    return min(int(rate_limits['reset']), int(rate_limits2['reset'])), (rate_limits['limit'] + rate_limits2['limit']), (rate_limits['remaining'] + rate_limits2['remaining'])

def stall_queries(next_reset, exit_event):
    delay = max(1, int(next_reset - time.time())) + 1
    if delay > 5:
        log.info("Stalling search queries with rate exceeded for the next %s seconds" % delay)
    breakable_sleep(delay, exit_event)

def read_search_state():
    with open(".search_state.json") as f:
        return {k: v for k, v in json.load(f).items()}

def write_search_state(state):
    with open(".search_state.json", "w") as f:
        json.dump(state, f)

# TODO
# - improve logs : add INFO on result of all queries on a keyword if new

def searcher(pile, searchco, searchco2, keywords, urlpieces, timed_keywords, locale, language, geocode, exit_event):
    # Search operators reference: https://developer.twitter.com/en/docs/tweets/search/guides/standard-operators
    try:
        next_reset, max_per_reset, left = get_twitter_rates(searchco, searchco2, retry=3)
    except Exception as e:
        log.error("Connecting to Twitter API: could not get rate limits %s: %s" % (type(e), e))
        sys.exit(1)
    curco = searchco

    queries = []
    fmtkeywords = []
    for k in keywords:
        if k.startswith("@"):
            queries.append(format_keyword(k))
        else:
            fmtkeywords.append(format_keyword(k))
    for q in urlpieces:
        fmtkeywords.append('url:"%s"' % format_url_query(q))
    if len(fmtkeywords) > 50:
        queries += [" OR ".join(a) for a in chunkize(fmtkeywords, 3)]
    else:
        queries += fmtkeywords
    timed_queries = {}
    state = {q: 0 for q in queries + [format_keyword(k) for k in timed_keywords.keys()]}
    try:
        queries_since_id = read_search_state()
        assert queries_since_id and sorted(state.keys()) == sorted(queries_since_id.keys())
        log.info("Search queries restarting from previous state.")
    except:
        queries_since_id = state

    timegap = 1 + len(queries)
    while not exit_event.is_set():
      try:
        if time.time() > next_reset:
            try:
                next_reset, _, left = get_twitter_rates(searchco, searchco2, retry=1)
            except Exception as e:
                log.error("Issue while collecting twitter rates, applying default 15 min values. %s: %s" % (type(e), e))
                next_reset += 15*60
                left = max_per_reset
        if not left:
            stall_queries(next_reset, exit_event)
            continue

        log.info("Starting search queries cycle with %d remaining calls for the next %s seconds" % (left, int(next_reset - time.time())))

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

        for query in [q[0] for q in sorted(queries_since_id.items(), key=lambda ts: ts[1])]:
            try:
                planning = timed_queries[query]
                if not planning:
                    continue
            except KeyError:
                planning = None

            since = queries_since_id[query]
            max_id = 0
            log.debug("Starting search query on %s since %s" % (query, since))
            while not exit_event.is_set():
                while not left and not exit_event.is_set():
                    try:
                        next_reset, _, left = get_twitter_rates(searchco, searchco2, retry=1)
                        if left:
                            log.debug("Resuming search with %d remaining calls for the next %s seconds" % (left, int(next_reset - time.time())))
                    except Exception as e:
                        log.debug("Issue while collecting twitter rates. %s: %s" % (type(e), e))
                    if not left:
                        stall_queries(next_reset, exit_event)

                args = {'q': query, 'count': 100, 'include_entities': True, 'result_type': 'recent', 'tweet_mode': 'extended'}
                if language:
                    args['lang'] = language
                if geocode:
                    args['geocode'] = geocode
                if max_id:
                    args['max_id'] = str(max_id)
                if queries_since_id[query]:
                    args['since_id'] = str(queries_since_id[query])
                try:
                    res = curco.search.tweets(**args)
                except:
                    curco = searchco if curco == searchco2 else searchco2
                    log.info("Switching search connexion to OAuth%s" % (2 if curco == searchco2 else ""))
                    try:
                        res = curco.search.tweets(**args)
                    except (TwitterHTTPError, BadStatusLine, URLError, SSLError) as e:
                        log.warning("Search connection could not be established, retrying in 2 secs (%s: %s)" % (type(e), e))
                        breakable_sleep(2, exit_event)
                        continue
                left -= 1
                try:
                    tweets = res['statuses']
                except KeyError:
                    log.warning("Bad response from Twitter to query %s with args %s: %s" % (query, args, res))
                    breakable_sleep(2, exit_event)
                    continue
                if not len(tweets):
                    break
                news = 0
                for tw in tweets:
                    tid = int(tw.get('id_str', str(tw.get('id', ''))))
                    if not tid:
                        continue
                    if since < tid:
                        since = tid + 1
                    if not max_id or max_id > tid:
                        max_id = tid - 1
                    if planning is not None:
                        ts = get_timestamp(tw["created_at"])
                        skip = True
                        for trang in planning:
                            if trang[0] < ts < trang[1]:
                                skip = False
                                break
                        if skip:
                            continue
                    tw["gazouilloire_source"] = "search"
                    pile.put(dict(tw))
                    news += 1
                if news == 0:
                    break
                log.debug("[search] +%d tweets (%s)" % (news, query))
            queries_since_id[query] = since
            write_search_state(queries_since_id)
        breakable_sleep(max(timegap, next_reset - time.time() - 2*left), exit_event)
      except KeyboardInterrupt:
        log.info( "closing searcher...")
        exit_event.set()
    log.info("FINISHED searcher")

def generate_geoloc_strings(x1, y1, x2, y2):
    streamgeocode = "%s,%s,%s,%s" % (y1, x1, y2, x2)
    log.info('Stream Bounding box: %s/%s -> %s/%s' % (x1, y1, x2, y2))
    x = old_div((x1 + x2), 2)
    y = old_div((y1 + y2), 2)
    d = 6371 * acos(sin(x*pi/180) * sin(x1*pi/180) + cos(x*pi/180) * cos(x1*pi/180) * cos((y1-y)*pi/180))
    searchgeocode = "%s,%s,%.2fkm" % (x, y, d)
    log.info('Search Disk: %s/%s, %.2fkm' % (x, y, d))
    return streamgeocode, searchgeocode

def main(conf):
    if len(conf['keywords']) + len(conf['url_pieces']) > 400:
        log.error('Please limit yourself to a maximum of 400 keywords total (including url_pieces): you set up %s keywords and %s url_pieces.' % (len(conf['keywords']), len(conf['url_pieces'])))
        sys.exit(1)
    try:
        oauth = OAuth(conf['twitter']['oauth_token'], conf['twitter']['oauth_secret'], conf['twitter']['key'], conf['twitter']['secret'])
        oauth2 = OAuth2(bearer_token=json.loads(Twitter(api_version=None, format="", secure=True, auth=OAuth2(conf['twitter']['key'], conf['twitter']['secret'])).oauth2.token(grant_type="client_credentials"))['access_token'])
        SearchConn = Twitter(domain="api.twitter.com", api_version="1.1", format="json", auth=oauth, secure=True)
        SearchConn2 = Twitter(domain="api.twitter.com", api_version="1.1", format="json", auth=oauth2, secure=True)
        ResConn = Twitter(domain="api.twitter.com", api_version="1.1", format="json", auth=oauth, secure=True)
        StreamConn = TwitterStream(domain="stream.twitter.com", api_version="1.1", auth=oauth, secure=True, block=False, timeout=10)
    except Exception as e:
        log.error('Could not initiate connections to Twitter API: %s %s' % (type(e), e))
        sys.exit(1)
    try:
        locale = timezone(conf['timezone'])
    except:
        log.error("\t".join(all_timezones)+"\n\n")
        log.error('Unknown timezone set in config.json: %s. Please choose one among the above ones.' % conf['timezone'])
        sys.exit(1)
    try:
        db = ElasticManager(**conf['database'])
        db.prepare_indices()
    except Exception as e:
        log.error('Could not initiate connection to database: %s %s' % (type(e), e))
        sys.exit(1)
    language = conf.get('language', None)
    streamgeocode = None
    searchgeocode = None
    if "geolocation" in conf and conf["geolocation"]:
        if type(conf["geolocation"]) == list:
            try:
                x1, y1, x2, y2 = conf["geolocation"]
                streamgeocode, searchgeocode = generate_geoloc_strings(x1, y1, x2, y2)
            except Exception as e:
                log.error('geolocation is wrongly formatted, should be something such as ["Lat1", "Long1", "Lat2", "Long2"]')
                sys.exit(1)
        else:
            GeoConn = Twitter(domain="api.twitter.com", api_version="1.1", format="json", auth=oauth, secure=True)
            res = GeoConn.geo.search(query=conf["geolocation"].replace(" ", "+"), granularity=conf.get("geolocation_type", "admin"), max_results=1)
            try:
                place = res["result"]["places"][0]
                log.info('Limiting tweets search to place "%s" with id "%s"' % (place['full_name'], place['id']))
                y1, x1 = place["bounding_box"]['coordinates'][0][0]
                y2, x2 = place["bounding_box"]['coordinates'][0][2]
                streamgeocode, searchgeocode = generate_geoloc_strings(x1, y1, x2, y2)
            except Exception as e:
                log.error('Could not find a place matching geolocation %s: %s %s' % (conf["geolocation"], type(e), e))
                sys.exit(1)
    grab_conversations = "grab_conversations" in conf and conf["grab_conversations"]
    resolve_links = "resolve_redirected_links" in conf and conf["resolve_redirected_links"]
    dl_medias = "download_medias" in conf and conf["download_medias"] and any(conf["download_medias"].values())
    if dl_medias:
        medias_types = set([k for k in conf["download_medias"] if conf["download_medias"][k]])
        medias_dir = conf.get("medias_directory", "medias")
        if not os.path.exists(medias_dir):
            os.makedirs(medias_dir)
    pile = Queue()
    pile_deleted = Queue()
    pile_catchup = Queue() if grab_conversations else None
    pile_medias = Queue() if dl_medias else None
    default_handler = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    exit_event = Event()
    depile = Process(target=depiler, args=(pile, pile_deleted, pile_catchup, pile_medias, conf['database'], locale, exit_event))
    depile.daemon = True
    depile.start()
    if grab_conversations:
        catchup = Process(target=catchupper, args=(pile, pile_catchup, ResConn, exit_event))
        catchup.daemon = True
        catchup.start()
    if resolve_links:
        resolve = Process(target=resolver, args=(RESOLVER_BATCH_SIZE, conf['database'], exit_event))
        resolve.daemon = True
        resolve.start()
    if dl_medias:
        download = Process(target=downloader, args=(pile_medias, medias_dir, medias_types, exit_event))
        download.daemon = True
        download.start()
    signal.signal(signal.SIGINT, default_handler)
    stream = Process(target=streamer, args=(pile, pile_deleted, StreamConn, ResConn, conf['keywords'], conf['url_pieces'], conf['time_limited_keywords'], locale, language, streamgeocode, exit_event))
    stream.daemon = True
    stream.start()
    search = Process(target=searcher, args=(pile, SearchConn, SearchConn2, conf['keywords'], conf['url_pieces'], conf['time_limited_keywords'], locale, language, searchgeocode, exit_event))
    search.start()
    def stopper(*args):
        exit_event.set()
    signal.signal(signal.SIGTERM, stopper)
    try:
        depile.join()
    except KeyboardInterrupt:
        exit_event.set()


if __name__=='__main__':
    main(load_conf("."))
