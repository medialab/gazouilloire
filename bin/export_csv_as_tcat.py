#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json, sys, re
from datetime import datetime
from pymongo import MongoClient

with open('config.json') as confile:
    conf = json.loads(confile.read())

db = MongoClient(conf['mongo']['host'], conf['mongo']['port'])[conf['mongo']['db']]['tweets']

def get_coords(tw):
    if 'coordinates' not in tw or not tw['coordinates']:
        tw['coordinates'] = {}
    if 'coordinates' not in tw['coordinates'] or not tw['coordinates']['coordinates']:
        tw['coordinates']['coordinates'] = ['', '']
    return tw['coordinates']['coordinates']

isodate = lambda x: datetime.strptime(x, '%a %b %d %H:%M:%S +0000 %Y').isoformat()

corresp_fields = {
    "id": "_id",
    "time": "timestamp",
    "created_at": lambda x: isodate(x['created_at']),
    "from_user_name": lambda x: x.get("user_screen_name", x.get("user_name", "")),
    "text": str,
    "filter_level": None,   # WTF is this?
    "possibly_sensitive": "possibly_sensitive",
    "withheld_copyright": str,
    "withheld_scope": str,
    "withheld_countries": lambda x: x.get("withheld_countries", []),      # Added since this is the most interesting info from withheld fields
    "truncated": bool,       # unnecessary since we rebuild text from RTs
    "retweet_count": int,
    "favorite_count": int,
    "lang": str,
    "to_user_name": "in_reply_to_screen_name",
    "in_reply_to_status_id": "in_reply_to_status_id_str",
    "source": str,
    "location": "user_location",
    "lat": lambda x: get_coords(x)[1],
    "lng": lambda x: get_coords(x)[0],
    "from_user_id": "user_id_str",
    "from_user_realname": "user_name",
    "from_user_verified": "user_verified",
    "from_user_description": "user_description",
    "from_user_url": "user_url",
    "from_user_profile_image_url": "user_profile_image_url_https",
    "from_user_utcoffset": "user_utc_offset",
    "from_user_timezone": "user_time_zone",
    "from_user_lang": "user_lang",
    "from_user_tweetcount": "user_statuses",
    "from_user_followercount": "user_followers",
    "from_user_friendcount": "user_friends",
    "from_user_favourites_count": "user_favourites",
    "from_user_listed": "user_listed",
    "from_user_withheld_scope": "user_withheld_scope",
    "from_user_withheld_countries": lambda x: x.get("user_withheld_countries", []),      # Added since this is the most interesting info from withheld fields
    "from_user_created_at": lambda x: isodate(x['user_created_at']),
    "links": lambda x: x.get("proper_links", x.get("links", [])),
    "medias": lambda x: [_id for _id,_url in x.get("medias", [])]
}

def search_field(field, tweet):
    if field not in corresp_fields:
        return tweet.get(field, '')
    if not corresp_fields[field]:
        return ''
    if corresp_fields[field] == bool:
        return tweet.get(field, False)
    if corresp_fields[field] == int:
        return tweet.get(field, 0)
    if corresp_fields[field] == str:
        return tweet.get(field, '')
    if type(corresp_fields[field]) == str:
        return tweet.get(corresp_fields[field], 0 if field.endswith('count') else '')
    else:
        return corresp_fields[field](tweet)

def format_field(val):
    if type(val) == bool:
        return "1" if val else "0"
    if type(val) == list:
        return u"|".join([v for v in val])
    if val == None:
        return ''
    return val if type(val) == unicode else unicode(val)

def get_field(field, tweet):
    return format_field(search_field(field, tweet)).replace('\n', ' ').replace('\r', ' ')

format_csv = lambda val: ('"%s"' % val.replace('"', '""') if "," in val or '"' in val else val).encode('utf-8')

keys = [
  "id",
  "time",
  "created_at",
  "from_user_name",
  "text",
  "filter_level",
  "possibly_sensitive",
  "withheld_copyright",
  "withheld_scope",
  "withheld_countries",
  "truncated",
  "retweet_count",
  "favorite_count",
  "lang",
  "to_user_name",
  "in_reply_to_status_id",
  "source",
  "location",
  "lat",
  "lng",
  "from_user_id",
  "from_user_realname",
  "from_user_verified",
  "from_user_description",
  "from_user_url",
  "from_user_profile_image_url",
  "from_user_utcoffset",
  "from_user_timezone",
  "from_user_lang",
  "from_user_tweetcount",
  "from_user_followercount",
  "from_user_friendcount",
  "from_user_favourites_count",
  "from_user_listed",
  "from_user_withheld_scope",
  "from_user_withheld_countries",
  "from_user_created_at",
  "links",
  "medias"
]
print ",".join(keys)
query = {}
if len(sys.argv) == 2:
    query = {"text": re.compile(sys.argv[1].replace(' ', '\s+'), re.I)}
elif len(sys.argv) > 2:
    query["$or"] = []
    for arg in sys.argv[1:]:
        query["$or"].append({"text": re.compile(arg.replace(' ', '\s+'), re.I)})
for t in db.find(query, sort=[("_id", -1)]):
    print ",".join(format_csv(get_field(k, t)) for k in keys)

