#/usr/bin/env python
# -*- coding: utf-8 -*-

import csv, sys
from pymongo import MongoClient, ASCENDING
from fake_useragent import UserAgent
from config import CSV_SOURCE, CSV_ENCODING, CSV_TWITTER_FIELD, MONGO_DATABASE, TWITTER
try:
    from config import CSV_LASTTWEET_FIELD
except:
    CSV_LASTTWEET_FIELD = None

from gazouilloire.run import resolve_url
from gazouilloire.tweets import prepare_tweet, clean_user_entities
from gazouilloire.api_wrapper import TwitterWrapper

with open(CSV_SOURCE) as f:
    data = list(csv.DictReader(f, delimiter=','))

api = TwitterWrapper(TWITTER)
db = MongoClient("localhost", 27017)[MONGO_DATABASE]

linkscoll = db['links']
tweetscoll = db['tweets']
for f in ['retweet_id', 'in_reply_to_status_id_str', 'timestamp',
          'links_to_resolve', 'lang', 'user_lang', 'langs']:
    tweetscoll.ensure_index([(f, ASCENDING)], background=True)
tweetscoll.ensure_index([('links_to_resolve', ASCENDING), ('_id', ASCENDING)], background=True)

api_field_call = 'screen_name'
if '--use-ids' in sys.argv:
    api_field_call = 'user_id'

for i, row in enumerate(data):
    user = {}
    for k in row.keys():
        user[k.decode(CSV_ENCODING)] = row[k].decode(CSV_ENCODING).replace(u' ', ' ').strip()
    user['twitter'] = user[CSV_TWITTER_FIELD].lstrip('@').lower()
    print "- WORKING ON %s" % user['twitter'], user
    new_last_tweet_id = 0L
    doneuser = db.users.find_one({'_id': user['twitter'])
    if doneuser:
        if CSV_LASTTWEET_FIELD:
            last_tweet_id = long(user.pop(CSV_LASTTWEET_FIELD))
            new_last_tweet_id = last_tweet_id
            if doneuser.get("last_tweet_id", 0L) > last_tweet_id:
                print "  ALREADY DONE!"
                continue
        elif doneuser.get("done"):
            print "  ALREADY DONE!"
            continue
    user['done'] = False
    api_args = {api_field_call: user['twitter']}
    metas = api.call('users.show', api_args)
    if not metas:
        print "SKIPPING tweets for %s whose account unfortunately disappeared" % user['twitter']
        continue
    clean_user_entities(metas)
    user.update(metas)
    user.pop('_id')
    db.users.update({'_id': user['twitter']}, {"$set": user}, upsert=True)
    if user['protected']:
        print "SKIPPING tweets for %s whose account is unfortunately protected" % user['twitter']
        continue
    api_args['count'] = 200
    api_args['contributor_details'] = 1
    api_args['include_rts'] = 1
    api_args['tweet_mode'] = "extended"
    if last_tweet_id:
        api_args["since_id"] = last_tweet_id
    tweets = api.call('statuses.user_timeline', api_args)
    while tweets:
        for tw in tweets:
            api_args['max_id'] = min(api_args.get('max_id', tw['id']), tw['id']-1)
            metas = prepare_tweet(tw)
            metas.pop('_id')
            tw.update(metas)
            for po in ['user', 'entities', 'extended_entities']:
                if po in tw:
                    tw.pop(po)
            db.tweets.update({'_id': tw['id']}, {"$set": tw}, upsert=True)
            if tw["id"] > new_last_tweet_id:
                new_last_tweet_id = tw["id"]
        print "...collected %s new tweets" % len(tweets)
        tweets = api.call('statuses.user_timeline', api_args)
    upd = {"done": True}
    if new_last_tweet_id:
        upd["last_tweet_id"] = new_last_tweet_id
    db.users.update({'_id': user['twitter']}, {"$set": upd})

print "Finished! You should now run links resolver on the db"
exit()

# TODO: refacto all of this with gazouilloire/run.py

ua = UserAgent()
ua.update()
todo = list(tweetscoll.find({"links_to_resolve": True}, projection={"links": 1, "proper_links": 1, "retweet_id": 1}, limit=600, sort=[("_id", 1)]))
left = tweetscoll.count({"links_to_resolve": True})
print "\n\n- STARTING LINKS RESOLVING: %s waiting\n\n" % left
while todo:
    done = 0
    urlstoclear = list(set([l for t in todo if not t.get("proper_links", []) for l in t.get('links', [])]))
    alreadydone = {l["_id"]: l["real"] for l in linkscoll.find({"_id": {"$in": urlstoclear}})}
    tweetsdone = []
    batchidsdone = set()
    for tweet in todo:
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
            print "          ", link
            good = resolve_url(link, user_agent=ua)
            gdlinks.append(good)
            try:
                linkscoll.save({'_id': link, 'real': good})
            except Exception as e:
                print "- WARNING: Could not store resolved link %s -> %s because %s: %s" % (link, good, type(e), e)
            if link != good:
                done += 1
        tweetscoll.update({'$or': [{'_id': tweetid}, {'retweet_id': tweetid}]}, {'$set': {'proper_links': gdlinks, 'links_to_resolve': False}}, upsert=False, multi=True)
        batchidsdone.add(tweetid)
    # clear tweets potentially rediscovered
    if tweetsdone:
        tweetscoll.update({"_id": {"$in": tweetsdone}}, {"$set": {"links_to_resolve": False}}, upsert=False, multi=True)
    if done:
        left = tweetscoll.count({"links_to_resolve": True})
        print "- [LINKS RESOLVING] +%s new redirection resolved out of %s links (%s waiting)" % (done, len(todo), left)
    todo = list(tweetscoll.find({"links_to_resolve": True}, projection={"links": 1, "proper_links": 1, "retweet_id": 1}, limit=600, sort=[("_id", 1)]))

