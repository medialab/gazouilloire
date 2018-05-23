#/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from pymongo import MongoClient, ASCENDING
from gazouilloire.tweets import prepare_tweet, clean_user_entities
from gazouilloire.api_wrapper import TwitterWrapper
from gazouilloire.web.export import export_csv


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

USER_FIELDS = [
  'id',
  'screen_name',
  'name',
  'description',
  'url',
  'lang',
  'created_at',
  'utc_offset',
  'time_zone',
  'location',
  'geo_enabled',
  'verified',
  'protected',
  'statuses_count',
  'followers_count',
  'friends_count',
  'favourites_count',
  'listed_count',
  'is_translator',
  'translator_type',
  'is_translation_enabled',
  'default_profile',
  'default_profile_image',
  'has_extended_profile',
  'profile_use_background_image',
  'profile_background_image_url_https',
  'profile_background_tile',
  'profile_background_color',
  'profile_banner_url',
  'profile_link_color',
  'profile_image_url',
  'profile_text_color',
  'profile_image_url_https',
  'profile_sidebar_fill_color',
  'profile_sidebar_border_color'
]
def export_users_metas(db, fields=USER_FIELDS):
    iterator = db.users.find(sort=[('screen_name', 1)])
    return export_csv(iterator, fields)

if __name__ == "__main__":
    from config import ACCOUNTS, MONGO_DATABASE, TWITTER
    api = TwitterWrapper(TWITTER)
    db = MongoClient("localhost", 27017)[MONGO_DATABASE]
    db.users.drop()
    process_accounts(ACCOUNTS, api, db)
    print export_users_metas(db).encode('utf-8')
