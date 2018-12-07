#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from builtins import str
import sys
import os
from pymongo import MongoClient, ASCENDING
sys.path.append(os.path.join(os.getcwd()))
from gazouilloire.tweets import prepare_tweet, clean_user_entities
from gazouilloire.api_wrapper import TwitterWrapper
from gazouilloire.web.export import export_csv, USER_FIELDS


def process_account(user_name, api, db):
    print("- WORKING ON %s" % user_name, file=sys.stderr)
    user_name = user_name.lstrip('@').strip().lower()
    if db.users.find({'screen_name': user_name, 'finished': True}, limit=1).count():
        print("  ALREADY DONE!", file=sys.stderr)
        return
    account_rt_field = "retweets_of_%s" % user_name
    db.users.ensure_index([(account_rt_field, ASCENDING)], background=True)

    user = {
      'screen_name': user_name,
      'finished': False
    }
    api_args = {
      'screen_name': user_name,
      'include_entities': True
    }
    metas = api.call('users.show', api_args)
    metas = clean_user_entities(metas)
    user.update(metas)
    db.users.update({'screen_name': user_name}, {"$set": user})

    if user['protected']:
        print("SKIPPING tweets for %s whose account is unfortunately protected" % user_name, file=sys.stderr)
        return

    api_args = {
      'user_id': user['id_str'],
      'count': 200,
      'trim_user': False,
      'exclude_replies': False,
      'include_rts': False,
      'tweet_mode': 'extended'
    }
    max_id = db.tweets.find_one({"user_id_str": user['id_str']}, projection=[], sort=[('timestamp', ASCENDING)])
    if max_id:
        api_args['max_id'] = int(max_id["_id"]) - 1
    tweets = api.call('statuses.user_timeline', api_args)
    while tweets:
        n_retweets_batch = 0
        for tweet in tweets:
            tw = prepare_tweet(tweet)
            api_args['max_id'] = min(api_args.get('max_id', tweet['id']), tweet['id'] - 1)
            if tw['retweet_id'] or not tw['retweet_count']:
                continue
            print(u"  - %s — %s" % (tw["text"].replace('\n', ' '), tw["url"]), file=sys.stderr)

            rt_args = {
              '_id': tweet['id'],
              'count': 100,
              'stringify_ids': False
            }
            user_args = {
              '_method': 'POST',
              'include_entities': True,
              'tweet_mode': 'extended'
            }
            retweeters = []
            tw["retweeters"] = []
            while rt_args.get('cursor', True):
                retweets = api.call('statuses.retweeters.ids', rt_args)
                rt_args['cursor'] = retweets.get('next_cursor', int(retweets.get('next_cursor_str', '')))
                rt_ids = retweets.get('ids', [])
                if rt_ids:
                    tw['retweeters'] += rt_ids
                    user_args['user_id'] = ",".join([str(i) for i in rt_ids])
                    retweeters += api.call('users.lookup', user_args)

            n_retweets = len(retweeters)
            n_retweets_batch += n_retweets
            print("    found %s retweets out of %s" % (n_retweets, tw["retweet_count"]), file=sys.stderr)
            if tw["retweeters"]:
                existing = [u["_id"] for u in db.users.find({"_id": {"$in": tw["retweeters"]}}, projection=[])]
                news = [clean_user_entities(u) for u in retweeters if u["id"] not in existing]
                if news:
                    db.users.insert(news)
                db.users.update({"_id": {"$in": tw["retweeters"]}}, {"$inc": {account_rt_field: 1}}, multi=True)
            db.tweets.update({'_id': tweet['id_str']}, {"$set": tw}, upsert=True)

        print(" -> collected %s tweets and %s retweets" % (len(tweets), n_retweets_batch), file=sys.stderr)
        tweets = api.call('statuses.user_timeline', api_args)

    db.users.update({'screen_name': user_name}, {"$set": {"finished": True}})


if __name__ == "__main__":
    from config import ACCOUNTS, MONGO_DATABASE, TWITTER
    api = TwitterWrapper(TWITTER)
    db = MongoClient("localhost", 27017)[MONGO_DATABASE]
    extra_fields = []
    for account in ACCOUNTS:
        process_account(account, api, db)
        extra_fields.append("retweets_of_%s" % account.lstrip('@').strip().lower())
    iterator = db.users.find()
    print(export_csv(iterator, USER_FIELDS, extra_fields).encode("utf-8"))
