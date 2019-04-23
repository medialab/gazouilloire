#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import unicode_literals
from builtins import str
import re, sys
from datetime import datetime

# More details on Twitter's tweets metadata can be read here: https://developer.twitter.com/en/docs/tweets/data-dictionary/overview/tweet-object
TWEET_FIELDS = [
  "id",                             # digital ID
  "time",                           # UNIX timestamp of creation
  "created_at",                     # ISO datetime of creation
  "from_user_name",                 # author's user text ID (@user)
  "text",                           # message's text content
  "filter_level",                   # internal TCAT field, ignorable
  "possibly_sensitive",             # whether a link present in the message might contain sensitive content according to Twitter
  "withheld_copyright",             # whether the tweet might be censored by Twitter following copyright requests, ignorable
  "withheld_scope",                 # whether the content withheld is the "status" or a "user", ignorable
  "withheld_countries",             # list of ISO country codes in which the message is withheld, separated by |, ignorable
  "truncated",                      # whether the tweet is bigger than 140 characters, obsolete
  "retweet_count",                  # number of retweets of the message (at collection time)
  "favorite_count",                 # number of likes of the message (at collection time)
  "reply_count",                    # number of answers to the message, dropped by Twitter (since Oct 17, now charged), unreliable and ignorable
  "lang",                           # language of the message automatically identified by Twitter's algorithms (equals "und" when no language could be detected)
  "to_user_name",                   # text ID of the user the message is answering to
  "to_user_id",                     # digital ID of the user the message is answering to
  "in_reply_to_status_id",          # digital ID of the tweet the message is answering to
  "source",                         # medium used by the user to post the message
  "source_name",                    # name of the medium used to post the message
  "source_url",                     # link to the medium used to post the message
  "location",                       # location declared in the user's profile (at collection time)
  "lat",                            # latitude of messages geolocalized
  "lng",                            # longitude of messages geolocalized
  "from_user_id",                   # author's user digital ID
  "from_user_realname",             # author's detailed textual name (at collection time)
  "from_user_verified",             # whether the author's account is certified
  "from_user_description",          # description given in the author's profile (at collection time)
  "from_user_url",                  # link to a website given in the author's profile (at collection time)
  "from_user_profile_image_url",    # link to the image avatar of the author's profile (at collection time)
  "from_user_utcoffset",            # time offset due to the user's timezone, dropped by Twitter (since May 18), ignorable
  "from_user_timezone",             # timezone declared in the user's profile, dropped by Twitter (since May 18), ignorable
  "from_user_lang",                 # language declared in the user's profile (at collection time), dropped by Twitter (since May 19), ignorable
  "from_user_tweetcount",           # number of tweets sent by the user (at collection time)
  "from_user_followercount",        # number of users following the author (at collection time)
  "from_user_friendcount",          # number of users the author is following (at collection time)
  "from_user_favourites_count",     # number of likes the author has expressed (at collection time)
  "from_user_listed",               # number of users lists the author has been included in (at collection time)
  "from_user_withheld_scope",       # whether the user content is withheld, ignorable
  "from_user_withheld_countries",   # list of ISO country codes in which the user content is withheld, separated by |, ignorable
  "from_user_created_at",           # ISO datetime of creation of the author's account
  "collected_via_thread",           # whether the tweet was retrieved only as part of a thread including a tweet matching the desired query
  "retweeted_id",                   # digital ID of the retweeted message
  "retweeted_user_name",            # text ID of the user who authored the retweeted message
  "retweeted_user_id",              # digital ID of the user who authoring the retweeted message
  "quoted_id",                      # digital ID of the retweeted message
  "quoted_user_name",               # text ID of the user who authored the retweeted message
  "quoted_user_id",                 # digital ID of the user who authoring the retweeted message
  "links",                          # list of links included in the text content, with redirections resolved, separated by |
  "medias_urls",                    # list of links to images/videos embedded, separated by |
  "medias_files",                   # list of filenames of images/videos embedded and downloaded, separated by |, ignorable when medias collections isn't enabled
  "mentioned_user_names",           # list of text IDs of users mentionned, separated by |
  "mentioned_user_ids",             # list of digital IDs of users mentionned, separated by |
  "hashtags"                        # list of hashtags used, lowercased, separated by |
]

# More details on Twitter's users metadata can be read here: https://developer.twitter.com/en/docs/tweets/data-dictionary/overview/user-object
USER_FIELDS = [
  'id',
  'screen_name',
  'name',
  'description',
  'url',
  'lang',                               # dropped from tweet objects only by Twitter (since May 19)
  'created_at',
  'utc_offset',                         # dropped by Twitter (since May 18), ignorable
  'time_zone',                          # dropped by Twitter (since May 18), ignorable
  'location',
  'geo_enabled',                        # dropped by Twitter (since May 19), ignorable
  'verified',
  'protected',
  'statuses_count',
  'followers_count',
  'friends_count',
  'favourites_count',
  'listed_count',
  'is_translator',                      # dropped by Twitter (since May 19), ignorable
  'translator_type',                    # dropped by Twitter (since May 19), ignorable
  'is_translation_enabled',             # dropped by Twitter (since May 19), ignorable
  'default_profile',
  'default_profile_image',
  'has_extended_profile',               # dropped by Twitter (since May 19), ignorable
  'profile_image_url',                  # dropped by Twitter (since May 19), ignorable
  'profile_image_url_https',
  'profile_banner_url',
  'profile_use_background_image',       # dropped by Twitter (since May 19), ignorable
  'profile_background_image_url',       # dropped by Twitter (since May 19), ignorable
  'profile_background_image_url_https', # dropped by Twitter (since May 19), ignorable
  'profile_background_tile',            # dropped by Twitter (since May 19), ignorable
  'profile_background_color',           # dropped by Twitter (since May 19), ignorable
  'profile_link_color',                 # dropped by Twitter (since May 19), ignorable
  'profile_text_color',                 # dropped by Twitter (since May 19), ignorable
  'profile_sidebar_fill_color',         # dropped by Twitter (since May 19), ignorable
  'profile_sidebar_border_color'        # dropped by Twitter (since May 19), ignorable
]

# Based and enriched from TCAT fields
CORRESP_FIELDS = {
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
    "reply_count": int,     # Recently appeared in Twitter data, and quickly became paid (~Oct 2017) : equals to None or 0 https://twittercommunity.com/t/reply-count-quote-count-not-available-in-statuses-lookup-answer/95241
    "lang": str,
    "to_user_name": "in_reply_to_screen_name",
    "to_user_id": "in_reply_to_user_id_str",    # Added for better user interaction analysis
    "in_reply_to_status_id": "in_reply_to_status_id_str",
    "source": str,
    "source_name": lambda x: re.split(r"[<>]", (x.get("source", "<>") or "<>"))[2],   # Added for simplier postprocess
    "source_url": lambda x: (x.get("source", '"') or '"').split('"')[1],             # Added for simplier postprocess
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
    "collected_via_thread": lambda x: bool(x.get("collected_via_thread") and not (x.get("collected_via_search") or x.get("collected_via_stream"))),
    "retweeted_id": "retweet_id",
    "retweeted_user_name": "retweet_user",
    "retweeted_user_id": "retweet_user_id",
    "quoted_id": "quoted_id",
    "quoted_user_name": "quoted_user",
    "quoted_user_id": "quoted_user_id",
    "links": lambda x: x.get("proper_links", x.get("links", [])),
    "medias_urls": lambda x: [_url for _id,_url in x.get("medias", [])],
    "medias_files": lambda x: [_id for _id,_url in x.get("medias", [])],
    "mentioned_user_names": lambda x: x.get("mentions_names", process_extract(x["text"], "@")),
    "mentioned_user_ids": "mentions_ids",
    "hashtags": lambda x: x.get("hashtags", process_extract(x["text"], "#"))
}

def search_field(field, tweet):
    if field not in CORRESP_FIELDS:
        return tweet.get(field, '')
    if not CORRESP_FIELDS[field]:
        return ''
    if CORRESP_FIELDS[field] == bool:
        return tweet.get(field, False)
    if CORRESP_FIELDS[field] == int:
        return tweet.get(field, 0)
    if CORRESP_FIELDS[field] == str:
        return tweet.get(field, '')
    # NOT THE MOST ELEGANT BUT THE ONLY WAY WE FOUND FOR PY2/PY3 COMPATIBILITY
    if type(CORRESP_FIELDS[field]) == type(''):
        return tweet.get(CORRESP_FIELDS[field], 0 if field.endswith('count') else '')

    else:
        try:
            return CORRESP_FIELDS[field](tweet)
        except Exception as e:
            print("WARNING: Can't apply export fonction for field %s (type %s) to tweet %s\n%s: %s" % (
                field, type(CORRESP_FIELDS[field]), tweet, type(e), e), file=sys.stderr)
            return ""

def format_field(val):
    if type(val) == bool:
        return "1" if val else "0"
    if type(val) == list:
        return u"|".join([v for v in val if v])
    if val == None:
        return ''
    return val if type(val) == str else str(val)

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

format_csv = lambda val: ('"%s"' % val.replace('"', '""') if "," in val or '"' in val else val)

def add_and_report(sett, val):
  leng = len(sett)
  sett.add(val)
  return len(sett) != leng

def get_thread_idset_from_idset(ids, mongocoll):
    ids_list = list(ids)
    all_ids = ids.copy()
    while ids_list:
        todo_ids = set()
        for t in mongocoll.find({"$or": [
            {"_id": {"$in": ids_list}},
            {"in_reply_to_status_id_str": {"$in": ids_list}}
          ]}, projection={"in_reply_to_status_id_str": 1}):
            if add_and_report(all_ids, t["_id"]):
                todo_ids.add(t["_id"])
            origin = t.get("in_reply_to_status_id_str")
            if origin and add_and_report(all_ids, origin):
                todo_ids.add(origin)
        ids_list = list(todo_ids)
    return all_ids

# Recursive version kept for archive but crashing for excessive recursion in some cases
def recursive_get_thread_idset_from_idset(ids, mongocoll, known_ids=set()):
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

def yield_csv(queryiterator, list_fields=TWEET_FIELDS, extra_fields=[]):
    out_fields = list_fields + extra_fields
    yield ",".join(out_fields).encode('utf-8')
    for t in queryiterator:
        # ignore tweets only caught on deletion missing most fields
        if len(t.keys()) < 10:
            continue
        yield ",".join(format_csv(get_field(k, t)) for k in out_fields)

def export_csv(queryiterator, list_fields=TWEET_FIELDS, extra_fields=[]):
    return "\n".join([t for t in yield_csv(queryiterator, list_fields, extra_fields)])

