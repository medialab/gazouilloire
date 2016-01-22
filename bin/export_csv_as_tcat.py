#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json, sys
from datetime import datetime
from pymongo import MongoClient

with open('config.json') as confile:
    conf = json.loads(confile.read())

db = MongoClient(conf['mongo']['host'], conf['mongo']['port'])[conf['mongo']['db']]['tweets']

print "id,time,created_at,from_user_name,text,filter_level,possibly_sensitive,withheld_copyright,withheld_scope,truncated,retweet_count,favorite_count,lang,to_user_name,in_reply_to_status_id,source,location,lat,lng,from_user_id,from_user_realname,from_user_verified,from_user_description,from_user_url,from_user_profile_image_url,from_user_utcoffset,from_user_timezone,from_user_lang,from_user_tweetcount,from_user_followercount,from_user_friendcount,from_user_favourites_count,from_user_listed,from_user_withheld_scope,from_user_created_at"

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
    "lat": lambda x: x.get('coordinates', {}).get('coordinates', ['', ''])[1],
    "lng": lambda x: x.get('coordinates', {}).get('coordinates', [''])[0],
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
    "created_at": lambda x: isodate(x['user_created_at'])
}

def format_field(val):
    if type(val) == bool:
        return 1 if val else 0
    if type(val) == list:
        return "|".join(val)
    return val

def search_field(field, tweet):
    if field not in corresp_fields:
        return tweet.get(field, '')
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

def get_field(field, tweet):
    return format_field(search_field(field, tweet))


for t in db.find(sort=[("_id", -1)]):
    ts = datetime.strptime(t['created_at'], '%a %b %d %H:%M:%S +0000 %Y').isoformat()
    coords = "::".join([str(a) for a in t["geo"]["coordinates"]]) if t["geo"] else ""
    text = '"' + t["text"].replace('"', '""').replace("\n", " ").replace("\r", "") + '"'
    name = t.get("user_screen_name", t.get("user_name", ""))
    print ",".join([a.encode("utf-8") for a in [t["url"],name,ts,t["lang"],coords,text]])

