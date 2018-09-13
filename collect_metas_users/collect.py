#/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from pymongo import MongoClient, ASCENDING
from gazouilloire.tweets import prepare_tweet, clean_user_entities
from gazouilloire.api_wrapper import TwitterWrapper
from gazouilloire.web.export import export_csv, USER_FIELDS


def process_accounts(list_users, api, db):

    user_args = {
      '_method': 'POST',
      'include_entities': True,
      'tweet_mode': 'extended'
    }
    while list_users:
        batch, list_users = list_users[:100], list_users[100:]
        user_args['screen_name'] = ",".join(batch)
        users = api.call('users.lookup', user_args)
        [clean_user_entities(u) for u in users]
        db.users.insert_many(users)
        print >> sys.stderr, " -> collected %s users (%s left todo)" % (len(users), len(list_users))


if __name__ == "__main__":
    from config import ACCOUNTS, MONGO_DATABASE, TWITTER
    api = TwitterWrapper(TWITTER)
    db = MongoClient("localhost", 27017)[MONGO_DATABASE]
    db.users.drop()
    process_accounts(ACCOUNTS, api, db)
    iterator = db.users.find(sort=[('screen_name', 1)])
    print export_csv(iterator, USER_FIELDS).encode("utf-8")
