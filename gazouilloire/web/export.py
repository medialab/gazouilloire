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
  "timestamp_utc",                  # UNIX timestamp of creation - UTC time
  "local_time",                     # ISO datetime of creation - local time
  "user_screen_name",               # author's user text ID (@user) (at collection time)
  "text",                           # message's text content
  # "filter_level",                   # maximum value of the filter_level parameter which may be used and still stream this Tweet
  "possibly_sensitive",             # whether a link present in the message might contain sensitive content according to Twitter
  # "withheld_copyright",             # whether the tweet might be censored by Twitter following copyright requests, ignorable
  # "withheld_scope",                 # whether the content withheld is the "status" or a "user", ignorable
  # "withheld_countries",             # list of ISO country codes in which the message is withheld, separated by |, ignorable
  # "truncated",                      # whether the tweet is bigger than 140 characters, obsolete
  "retweet_count",                  # number of retweets of the message (at collection time)
  "like_count",                     # number of likes of the message (at collection time)
  "reply_count",                    # number of answers to the message, dropped by Twitter (since Oct 17, now charged), unreliable and ignorable
  "lang",                           # language of the message automatically identified by Twitter's algorithms (equals "und" when no language could be detected)
  "to_username",                    # text ID of the user the message is answering to
  "to_userid",                      # digital ID of the user the message is answering to
  "to_tweetid",                     # digital ID of the tweet the message is answering to
  # "source",                         # medium used by the user to post the message, now exported in source_name and source_url fields
  "source_name",                    # name of the medium used to post the message
  "source_url",                     # link to the medium used to post the message
  "user_location",                  # location declared in the user's profile (at collection time)
  "lat",                            # latitude of messages geolocalized
  "lng",                            # longitude of messages geolocalized
  "user_id",                        # author's user digital ID
  "user_name",                      # author's detailed textual name (at collection time)
  "user_verified",                  # whether the author's account is certified
  "user_description",               # description given in the author's profile (at collection time)
  "user_url",                       # link to a website given in the author's profile (at collection time)
  "user_image",                     # link to the image avatar of the author's profile (at collection time)
  # "user_utcoffset",                 # time offset due to the user's timezone, dropped by Twitter (since May 18), ignorable
  # "user_timezone",                  # timezone declared in the user's profile, dropped by Twitter (since May 18), ignorable
  # "user_lang",                      # language declared in the user's profile (at collection time), dropped by Twitter (since May 19), ignorable
  "user_tweets",                    # number of tweets sent by the user (at collection time)
  "user_followers",                 # number of users following the author (at collection time)
  "user_friends",                   # number of users the author is following (at collection time)
  "user_likes",                     # number of likes the author has expressed (at collection time)
  "user_lists",                    # number of users lists the author has been included in (at collection time)
  "user_created_at",                # ISO datetime of creation of the author's account
  "user_timestamp_utc",             # UNIX timestamp of creation of the author's account - UTC time
  "collected_via",                  # How we received the message: "stream", "search", "retweet" (the original tweet was
                                    # contained in the retweet metadata), "quote" (the original tweet was contained in
                                    # the quote metadata), "thread" (the tweet is part of the same conversation as a
                                    # tweet collected via search or stream). If the message was collected via multiple
                                    # ways, they are separated by |
  "match_query",                    # whether the tweet was retrieved because it matches the query, or whether it was
                                    # collected via "quote" or "thread"
  "retweeted_id",                   # digital ID of the retweeted message
  "retweeted_user",                 # text ID of the user who authored the retweeted message
  "retweeted_user_id",              # digital ID of the user who authoring the retweeted message
  "retweeted_timestamp_utc",        # UNIX timestamp of creation of the retweeted message - UTC time
  "quoted_id",                      # digital ID of the retweeted message
  "quoted_user",                    # text ID of the user who authored the quoted message
  "quoted_user_id",                 # digital ID of the user who authoring the quoted message
  "quoted_timestamp_utc",           # UNIX timestamp of creation of the quoted message - UTC time
  "collection_time",                # ISO datetime of message collection - local time
  "url",                            # url of the tweet (to get a view of the message directly on Twitter)
  "place_country_code",             # if the tweet has an associated 'place', country code of that place
  "place_name",                     # if the tweet has an associated 'place', name of that place
  "place_type",                     # if the tweet has an associated 'place', type of that place ('city', 'admin', etc.)
  "place_coordinates",              # if the tweet has an associated 'place', coordinates of that place, separated by |
  "links",                          # list of links included in the text content, with redirections resolved, separated by |
  "media_urls",                     # list of links to images/videos embedded, separated by |
  "media_files",                    # list of filenames of images/videos embedded and downloaded, separated by |, ignorable when medias collections isn't enabled
  "media_types",                    # list of media types (photo, video, animated gif), separated by |
  "mentioned_names",                # list of text IDs of users mentionned, separated by |
  "mentioned_ids",                  # list of digital IDs of users mentionned, separated by |
  "hashtags"                        # list of hashtags used, lowercased, separated by |
]

# More details on Twitter's users metadata can be read here: https://developer.twitter.com/en/docs/tweets/data-dictionary/overview/user-object
USER_FIELDS = [
  'id',
  'screen_name',
  'name',
  'description',
  'url',
  # 'lang',                               # dropped from tweet objects only by Twitter (since May 19)
  'created_at',
  # 'utc_offset',                         # dropped by Twitter (since May 18), ignorable
  # 'time_zone',                          # dropped by Twitter (since May 18), ignorable
  'location',
  # 'geo_enabled',                        # dropped by Twitter (since May 19), ignorable
  'verified',
  'protected',
  'tweets',
  'followers',
  'friends',
  'likes',
  'lists',
  # 'is_translator',                      # dropped by Twitter (since May 19), ignorable
  # 'translator_type',                    # dropped by Twitter (since May 19), ignorable
  # 'is_translation_enabled',             # dropped by Twitter (since May 19), ignorable
  # 'default_profile',
  # 'default_profile_image',
  # 'has_extended_profile',               # dropped by Twitter (since May 19), ignorable
  # 'profile_image_url',                  # dropped by Twitter (since May 19), ignorable
  'image',
  # 'profile_banner_url',
  # 'profile_use_background_image',       # dropped by Twitter (since May 19), ignorable
  # 'profile_background_image_url',       # dropped by Twitter (since May 19), ignorable
  # 'profile_background_image_url_https', # dropped by Twitter (since May 19), ignorable
  # 'profile_background_tile',            # dropped by Twitter (since May 19), ignorable
  # 'profile_background_color',           # dropped by Twitter (since May 19), ignorable
  # 'profile_link_color',                 # dropped by Twitter (since May 19), ignorable
  # 'profile_text_color',                 # dropped by Twitter (since May 19), ignorable
  # 'profile_sidebar_fill_color',         # dropped by Twitter (since May 19), ignorable
  # 'profile_sidebar_border_color'        # dropped by Twitter (since May 19), ignorable
]

# Based and enriched from TCAT fields
CORRESP_FIELDS = {
    "id": str,
    "timestamp_utc": str,
    "local_time": str,
    "user_screen_name": str,
    "text": str,
    "possibly_sensitive": bool,
    "retweet_count": int,
    "like_count": int,
    "reply_count": int,     # Recently appeared in Twitter data, and quickly dropped as it became paid (~Oct 2017) : equals to None or 0 https://twittercommunity.com/t/reply-count-quote-count-not-available-in-statuses-lookup-answer/95241
    "lang": str,
    "to_username": str,
    "to_userid": str,    # Added for better user interaction analysis
    "to_tweetid": str,
    "source_name": str,
    "source_url": str,
    "user_location": str,
    "lat": str,
    "lng": str,
    "user_id": str,
    "user_name": str,
    "user_verified": bool,
    "user_description": str,
    "user_url": str,
    "user_image": str,
    # "user_utcoffset": "user_utc_offset",   # Not available anymore after 2018-05-23 #RGPD https://twittercommunity.com/t/upcoming-changes-to-the-developer-platform/104603
    # "user_timezone": "user_time_zone",     # Not available anymore after 2018-05-23 #RGPD https://twittercommunity.com/t/upcoming-changes-to-the-developer-platform/104603
    "user_tweets": int,
    "user_followers": int,
    "user_friends": int,
    "user_likes": int,
    "user_lists": int,
    "user_created_at": str,
    # More added fields:
    "collected_via": str,
    "match_query": bool,
    "retweeted_id": str,
    "retweeted_user_name": str,
    "retweeted_user_id": str,
    "retweeted_timestamp_utc": str,
    "quoted_id": str,
    "quoted_user": str,
    "quoted_user_id": str,
    "quoted_timestamp_utc": str,
    "links": lambda x: x.get("proper_links", x.get("links", [])),
    "media_urls": str,
    "media_files": str,
    "mentioned_names": str,
    "mentioned_ids": str,
    "hashtags": "hashtags",
    "place_coordinates": "place_coordinates",
    "place_country_code": str,
    "place_name": str,
    "place_type": str,
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
    # out_fields = list_fields + extra_fields
    # yield ",".join(out_fields)
    for t in queryiterator:
        source = t["_source"]
        # ignore tweets only caught on deletion missing most fields
        if len(source) < 10:
            continue
        source["id"] = t["_id"]
        source["links"] = source.get("proper_links", source.get("links", []))
        for multiple in ["links", "hashtags", "collected_via", "media_urls", "media_files", "mentioned_names",
                         "mentioned_ids", "place_coordinates"]:
            source[multiple] = "|".join(str(i) for i in source[multiple]) if multiple in source else ''
        for boolean in ["possibly_sensitive", "user_verified", "match_query"]:
            source[boolean] = int(source[boolean]) if boolean in source else ''

        yield source


def export_csv(queryiterator, list_fields=TWEET_FIELDS, extra_fields=[]):
    return "\n".join([t for t in yield_csv(queryiterator, list_fields, extra_fields)])

