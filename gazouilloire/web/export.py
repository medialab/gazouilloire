#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re, sys
from datetime import datetime

fields = [
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
  "reply_count",
  "lang",
  "to_user_name",
  "to_user_id",
  "in_reply_to_status_id",
  "source",
  "source_name",
  "source_url",
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
  "retweeted_id",
  "retweeted_user_name",
  "retweeted_user_id",
  "links",
  "medias_urls",
  "medias_files",
  "mentioned_user_names",
  "mentioned_user_ids",
  "hashtags"
]

# Based and enriched from TCAT fields
corresp_fields = {
    "id": "_id",
    "time": "timestamp",
    "created_at": lambda x: isodate(x.get("created_at", "")),
    "from_user_name": lambda x: x.get("user_screen_name", x.get("user_name", "")),
    "text": str,
    "filter_level": None,   # WTF is this?
    "possibly_sensitive": "possibly_sensitive",
    "withheld_copyright": str,
    "withheld_scope": str,
    "withheld_countries": lambda x: x.get("withheld_countries", []),      # Added since this is the most interesting info from withheld fields
    "truncated": bool,      # unnecessary since we rebuild text from RTs
    "retweet_count": int,
    "favorite_count": int,
    "reply_count": int,     # Recently appeared in Twitter data
    "lang": str,
    "to_user_name": "in_reply_to_screen_name",
    "to_user_id": "in_reply_to_user_id_str",    # Added for better user interaction analysis
    "in_reply_to_status_id": "in_reply_to_status_id_str",
    "source": str,
    "source_name": lambda x: re.split(r"[<>]", x.get("source", "<>"))[2],   # Added for simplier postprocess
    "source_url": lambda x: x.get("source", '"').split('"')[1],             # Added for simplier postprocess
    "location": "user_location",
    "lat": lambda x: get_coords(x)[1],
    "lng": lambda x: get_coords(x)[0],
    "from_user_id": "user_id_str",
    "from_user_realname": "user_name",
    "from_user_verified": "user_verified",
    "from_user_description": "user_description",
    "from_user_url": "user_url",
    "from_user_profile_image_url": "user_profile_image_url_https",
    "from_user_utcoffset": "user_utc_offset",   # Not available anymore after 2018-05-23 #RGPD https://twittercommunity.com/t/upcoming-changes-to-the-developer-platform/104603
    "from_user_timezone": "user_time_zone",     # Not available anymore after 2018-05-23 #RGPD https://twittercommunity.com/t/upcoming-changes-to-the-developer-platform/104603
    "from_user_lang": "user_lang",
    "from_user_tweetcount": "user_statuses",
    "from_user_followercount": "user_followers",
    "from_user_friendcount": "user_friends",
    "from_user_favourites_count": "user_favourites",
    "from_user_listed": "user_listed",
    "from_user_withheld_scope": "user_withheld_scope",
    "from_user_withheld_countries": lambda x: x.get("user_withheld_countries", []),      # Added since this is the most interesting info from withheld fields
    "from_user_created_at": lambda x: isodate(x.get("user_created_at", "")),
    # More added fields:
    "retweeted_id": "retweet_id",
    "retweeted_user_name": "retweet_user",
    "retweeted_user_id": "retweet_user_id",
    "links": lambda x: x.get("proper_links", x.get("links", [])),
    "medias_urls": lambda x: [_url for _id,_url in x.get("medias", [])],
    "medias_files": lambda x: [_id for _id,_url in x.get("medias", [])],
    "mentioned_user_names": lambda x: x.get("mentions_names", process_extract(x["text"], "@")),
    "mentioned_user_ids": "mentions_ids",
    "hashtags": lambda x: x.get("hashtags", process_extract(x["text"], "#"))
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
        try:
            return corresp_fields[field](tweet)
        except Exception as e:
            print >> sys.stderr, "WARNING: Can't apply export fonction for field %s to tweet %s\n%s: %s" % (field, tweet, type(e), e)
            return ""

def format_field(val):
    if type(val) == bool:
        return "1" if val else "0"
    if type(val) == list:
        return u"|".join([v for v in val if v])
    if val == None:
        return ''
    return val if type(val) == unicode else unicode(val)

def get_field(field, tweet):
    return format_field(search_field(field, tweet)).replace('\n', ' ').replace('\r', ' ')

re_clean_rt = re.compile(r"^RT @\w+: ")
def process_extract(text, car):
    return sorted([r.lstrip(car).lower() for r in re.split(r'[^\w%s]+' % car, re_clean_rt.sub('', text)) if r.startswith(car)])

def get_coords(tw):
    if 'coordinates' not in tw or not tw['coordinates']:
        tw['coordinates'] = {}
    if 'coordinates' not in tw['coordinates'] or not tw['coordinates']['coordinates']:
        tw['coordinates']['coordinates'] = ['', '']
    return tw['coordinates']['coordinates']

isodate = lambda x: datetime.strptime(x, '%a %b %d %H:%M:%S +0000 %Y').isoformat()

format_csv = lambda val: ('"%s"' % val.replace('"', '""') if "," in val or '"' in val else val).encode('utf-8')

def get_thread_idset_from_idset(ids, mongocoll, known_ids=set()):
    all_ids = ids | known_ids
    new_ids = set()
    ids_list = list(ids)
    for t in mongocoll.find({"$or": [
        {"_id": {"$in": ids_list}},
        {"in_reply_to_status_id_str": {"$in": ids_list}}
      ]}, projection={"in_reply_to_status_id_str": 1}):
        if t["_id"] not in all_ids:
            new_ids.add(t["_id"])
        origin = t.get("in_reply_to_status_id_str")
        if origin and origin not in all_ids:
            new_ids.add(origin)
    if len(new_ids):
        return all_ids | get_thread_idset_from_idset(new_ids, mongocoll, all_ids)
    return all_ids

def get_thread_ids_from_ids(ids_list, mongocoll):
    return list(get_thread_idset_from_idset(set(ids_list), mongocoll))

def get_thread_ids_from_query(query, mongocoll):
    ids = [t["_id"] for t in mongocoll.find(query, projection={})]
    return get_thread_ids_from_ids(ids, mongocoll)

def yield_csv(queryiterator, extra_fields=[]):
    out_fields = fields + extra_fields
    yield ",".join(out_fields)
    for t in queryiterator:
        yield ",".join(format_csv(get_field(k, t)) for k in out_fields)

def export_csv(queryiterator, extra_fields=[]):
    return "\n".join([t.decode('utf-8') for t in yield_csv(queryiterator, extra_fields)])
