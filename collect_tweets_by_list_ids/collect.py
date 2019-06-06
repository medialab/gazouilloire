#/usr/bin/env python
# -*- coding: utf-8 -*-

import sys, csv
import progressbar
from pymongo import MongoClient, ASCENDING
from fake_useragent import UserAgent

from config import MONGO_DATABASE, TWITTER

from gazouilloire.run import resolve_url
from gazouilloire.tweets import prepare_tweets
from gazouilloire.api_wrapper import TwitterWrapper


def init_mongodb(db):
    tweetscoll = db['tweets']
    for f in ['retweet_id', 'in_reply_to_status_id_str', 'timestamp',
              'links_to_resolve', 'lang', 'user_lang', 'langs']:
        tweetscoll.ensure_index([(f, ASCENDING)], background=True)
    tweetscoll.ensure_index([('links_to_resolve', ASCENDING), ('_id', ASCENDING)], background=True)

def collect_tweets(api, db, list_ids):
    n_expected = len(list_ids)
    tweets = api.call(
      'statuses.lookup',
      {
        '_id': ','.join(list_ids),
        'include_entities': True,
        'include_ext_alt_text': True,
        'include_card_uri': True,
        'map': True,
        'tweet_mode': 'extended',
        '_method': 'POST'
      }
    )
    n_answered = len(tweets)
    processed = list(prepare_tweets(tweets["id"].values(), None))
    n_returned = len(processed)
    processed_ids = [t["_id"] for t in processed]
    db.tweets.delete_many({"_id": {"$in": processed_ids}})
    db.tweets.insert_many(processed)
    return (n_returned, n_answered, n_expected)

# TODO: refacto all of this with gazouilloire/run.py
def resolve_links(db):
    tweetscoll = db['tweets']
    linkscoll = db['links']
    ua = UserAgent()
    ua.update()
    todo = list(tweetscoll.find({"links_to_resolve": True}, projection={"links": 1, "proper_links": 1, "retweet_id": 1}, limit=600, sort=[("_id", 1)]))
    left = tweetscoll.count({"links_to_resolve": True})
    print >> sys.stderr, "\n\n- STARTING LINKS RESOLVING: %s waiting\n\n" % left
    while todo:
        done = 0
        urlstoclear = list(set([l for t in todo if not t.get("proper_links", []) for l in t.get('links', [])]))
        alreadydone = {l["_id"]: l["real"] for l in linkscoll.find({"_id": {"$in": urlstoclear}})}
        tweetsdone = []
        batchidsdone = set()
        ct = 0
        for tweet in todo:
            ct += 1
            if tweet.get("proper_links", []):
                tweetsdone.append(tweet["_id"])
                continue
            tweetid = tweet.get('retweet_id') or tweet['_id']
            if tweetid in batchidsdone:
                continue
            gdlinks = []
            for link in tweet.get("links", []):
                if link in alreadydone:
                    gdlinks.append(alreadydone[link])
                    continue
                print >> sys.stderr, "    %s / %s  " % (ct, left), link
                good = resolve_url(link, user_agent=ua)
                gdlinks.append(good)
                alreadydone[link] = good
                try:
                    linkscoll.save({'_id': link, 'real': good})
                    if good != link:
                        print >> sys.stderr, "              ->", good
                except Exception as e:
                    print >> sys.stderr, "- WARNING: Could not store resolved link %s -> %s because %s: %s" % (link, good, type(e), e)
                if link != good:
                    done += 1
            tweetscoll.update({'$or': [{'_id': tweetid}, {'retweet_id': tweetid}]}, {'$set': {'proper_links': gdlinks, 'links_to_resolve': False}}, upsert=False, multi=True)
            batchidsdone.add(tweetid)
        # clear tweets potentially rediscovered
        if tweetsdone:
            tweetscoll.update({"_id": {"$in": tweetsdone}}, {"$set": {"links_to_resolve": False}}, upsert=False, multi=True)
        if done:
            left = tweetscoll.count({"links_to_resolve": True})
            print >> sys.stderr, "- [LINKS RESOLVING] +%s new redirection resolved out of %s links (%s waiting)" % (done, len(todo), left)
        todo = list(tweetscoll.find({"links_to_resolve": True}, projection={"links": 1, "proper_links": 1, "retweet_id": 1}, limit=600, sort=[("_id", 1)]))

if __name__ == "__main__":
    INPUT_CSV = sys.argv[1]
    try:
        IDS_FIELD = sys.argv[2]
    except:
        IDS_FIELD = "id"
    try:
        DELIMITER = sys.argv[3]
    except:
        DELIMITER = ','

    api = TwitterWrapper(TWITTER)
    db = MongoClient("localhost", 27017)[MONGO_DATABASE]
    init_mongodb(db)

    try:
        with open(INPUT_CSV) as f:
            data = csv.DictReader(f, delimiter=DELIMITER)
            count = 0
            for row in data:
                count += 1
                if IDS_FIELD not in row:
                    print >> sys.stderr, "ERROR: there is no column named '%s' in %s" % (IDS_FIELD, INPUT_CSV)
                    print >> sys.stderr, row.keys()
                    exit(1)
    except Exception as e:
        print >> sys.stderr, "ERROR collecting %s: %s" % (type(e), e)
        exit(1)

    bar = progressbar.ProgressBar(max_value=count)
    with open(INPUT_CSV) as f:
        ct = 0
        list_ids = []
        for row in bar(csv.DictReader(f, delimiter=DELIMITER), max_value=count):
            ct +=1
            list_ids.append(row[IDS_FIELD])
            if ct % 100 == 0:
                collect_tweets(api, db, list_ids)
                list_ids = []
        if list_ids:
            collect_tweets(api, db, list_ids)

    resolve_links(db)

