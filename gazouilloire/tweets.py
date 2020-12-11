# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import unicode_literals
from builtins import str
from builtins import chr
import re
import time
try:
    from html.entities import name2codepoint
except ImportError:
    from htmlentitydefs import name2codepoint
from pytz import timezone
from datetime import datetime
from gazouilloire.url_resolve import normalize
from gazouilloire.config_format import log

re_entities = re.compile(r'&([^;]+);')

CORRESP_FIELDNAMES = {
    "in_reply_to_status_id_str": "to_tweetid",
    "in_reply_to_screen_name": "to_username",
    "in_reply_to_user_id_str": "to_userid",
    "lang": "lang",
    "coordinates": "coordinates",
    "possibly_sensitive": "possibly_sensitive",
    "retweet_count": "retweet_count",
    "favorite_count": "like_count",
    "reply_count": "reply_count"
}

def decode_entities(x):
    if x.group(1).startswith('#'):
        char = x.group(1)[1:]
        if char.startswith('x'):
            try:
                return chr(int(x.group(1)[2:], 16))
            except:
                pass
        try:
            return chr(int(x.group(1)[1:]))
        except:
            pass
    try:
        return chr(name2codepoint[x.group(1)])
    except:
        return x.group(1)


def unescape_html(text):
    return re_entities.sub(decode_entities, text)

re_clean_rt = re.compile(r"^RT @\w+: ")
def process_extract(text, car):
    return sorted(set([r.lstrip(car).lower() for r in re.split(r'[^\w%s]+' % car, re_clean_rt.sub('', text)) if r.startswith(car)]))


def get_dates(t, locale, field='created_at'):
    tim = datetime.strptime(t[field], '%a %b %d %H:%M:%S +0000 %Y')
    if locale:
        utc_date = timezone('UTC').localize(tim)
        locale_date = utc_date.astimezone(locale)
        return str(utc_date.timestamp()), datetime.strftime(locale_date, "%Y-%m-%dT%H:%M:%S")
    return str(tim.timestamp()), datetime.strftime(tim, "%Y-%m-%dT%H:%M:%S")


def nostr_field(f): return f.replace('_str', '')


def grab_extra_meta(source, result, locale=None):
    for meta in ["in_reply_to_status_id_str", "in_reply_to_screen_name", "in_reply_to_user_id_str", "lang", "coordinates", "possibly_sensitive", "retweet_count", "favorite_count", "reply_count"]:
        if meta in source:
            if not isinstance(source[meta], dict):
                result[CORRESP_FIELDNAMES[meta]] = source[meta]
            elif meta != "coordinates":
                log.warning("field {} is dict. It contains the following keys: {}. The field will NOT be indexed"
                      .format(meta, " ".join(sorted(source[meta].keys()))))
            else:
                result["coordinates"] = source["coordinates"]["coordinates"]
                result["lat"] = source["coordinates"]["coordinates"][1]
                result["lng"] = source["coordinates"]["coordinates"][0]
        elif nostr_field(meta) in source:
            result[meta] = str(source[nostr_field(meta)])
    for meta in ['id_str', 'screen_name', 'name', 'friends_count', 'followers_count', 'location', 'verified', 'description', 'created_at']:
        key = "user_%s" % meta.replace('_count', '')
        if key in source:
            result[nostr_field(key)] = source[key]
        elif nostr_field(key) in source:
            result[nostr_field(key)] = str(source[nostr_field(key)])
        elif 'user' in source and meta in source['user']:
            result[nostr_field(key)] = source['user'][meta]
        elif 'user' in source and nostr_field(meta) in source['user']:
            result[nostr_field(key)] = source['user'][nostr_field(meta)]
    if "user" in source:
        result["user_tweets"] = source["user"]["statuses_count"]
        result["user_likes"] = source["user"]["favourites_count"]
        result["user_lists"] = source["user"]["listed_count"]
        result["user_image"] = source["user"]["profile_image_url_https"]
    if "place" in source and source["place"] is not None:
        for meta in ['country_code', 'full_name', 'place_type']:
            if meta in source['place']:
                key = "place_%s" % meta.replace('place_', '').replace('full_', '')
                result[key] = source['place'][meta]
        if "bounding_box" in source["place"] and "coordinates" in source["place"]["bounding_box"]:
            result["place_coordinates"] = source["place"]["bounding_box"]["coordinates"][0]
    try:
        result['user_url'] = source['user']['entities']['url']['urls'][0]['expanded_url']
    except:
        try:
            result['user_url'] = source['user']['url']
        except:
            pass
    try:
        result['user_timestamp_utc'], result['user_created_at'] = get_dates(
            result, locale, 'user_created_at')
    except:
        pass
    if "source" in source and source["source"]:
        split_source = source['source'].replace('<a href="', '').replace('</a>', '').split('" rel="nofollow">')
        result['source_url'] = split_source[0]
        result['source_name'] = split_source[1]
    return result


def prepare_tweets(tweets, locale):
    for tweet in tweets:
        if not isinstance(tweet, dict):
            continue
        if "_id" not in tweet:
            for subtweet in prepare_tweet(tweet, locale=locale):
                yield subtweet
        else:
            yield tweet


def prepare_tweet(tweet, locale=None):
    results = []
    if "extended_tweet" in tweet:
        for field in tweet["extended_tweet"]:
            tweet[field] = tweet["extended_tweet"][field]
    text = tweet.get('full_text', tweet.get('text', ''))
    if not text:
        log.warning("no text for tweet %s" % "https://twitter.com/%s/statuses/%s" %
              (tweet['user']['screen_name'], tweet['id_str']))
    rti = None
    rtu = None
    rtuid = None
    rtime = None
    if "retweeted_status" in tweet and tweet['retweeted_status']['id_str'] != tweet['id_str']:
        rti = tweet['retweeted_status']['id_str']
        rtu = tweet['retweeted_status']['user']['screen_name']
        rtuid = tweet['retweeted_status']['user']['id_str']
        tweet['retweeted_status']["gazouilloire_source"] = "retweet"
        nested = prepare_tweet(tweet['retweeted_status'], locale=locale)
        rtweet = nested[-1]
        results.extend(nested)
        rtime = rtweet['timestamp_utc']
        text = "RT @%s: %s" % (rtu, rtweet['text'])
        for ent in ['entities', 'extended_entities']:
            if ent not in tweet['retweeted_status']:
                continue
            tweet[ent] = tweet.get(ent, {})
            for field in tweet['retweeted_status'][ent]:
                tweet[ent][field] = tweet[ent].get(field, [])
                if field in tweet['retweeted_status'][ent]:
                    tweet[ent][field] += tweet['retweeted_status'][ent][field]
    qti = None
    qtu = None
    qtuid = None
    qtime = None
    if "quoted_status" in tweet and tweet['quoted_status']['id_str'] != tweet['id_str']:
        qti = tweet['quoted_status']['id_str']
        qtu = tweet['quoted_status']['user']['screen_name']
        qtuid = tweet['quoted_status']['user']['id_str']
        tweet['quoted_status']["gazouilloire_source"] = "quote"
        nested = prepare_tweet(tweet['quoted_status'], locale=locale)
        qtweet = nested[-1]
        results.extend(nested)
        if 'quoted_status_permalink' in tweet:
            qturl = tweet['quoted_status_permalink']['url']
        else:
            qturl = qtweet['url']
        qtime = qtweet['timestamp_utc']
        text = text.replace(qturl, u"« %s: %s — %s »" %
                            (qtu, qtweet['text'], qturl))
        for ent in ['entities', 'extended_entities']:
            if ent not in tweet['quoted_status']:
                continue
            tweet[ent] = tweet.get(ent, {})
            for field in tweet['quoted_status'][ent]:
                tweet[ent][field] = tweet[ent].get(field, [])
                if field in tweet['quoted_status'][ent]:
                    tweet[ent][field] += tweet['quoted_status'][ent][field]
    medids = set()
    media_urls = []
    media_files = []
    media_types = []
    links = set()
    hashtags = set()
    mentions = {}
    if 'entities' in tweet or 'extended_entities' in tweet:
        source_id = rti or qti or tweet['id_str']
        for entity in tweet.get('extended_entities', tweet['entities']).get('media', []) + tweet['entities'].get('urls', []):
            if 'expanded_url' in entity and 'url' in entity and entity['expanded_url']:
                try:
                    text = text.replace(entity['url'], entity['expanded_url'])
                except:
                    pass
            if "media_url" in entity:
                if "video_info" in entity:
                    med_url = sorted(entity["video_info"]["variants"], key=lambda x: x.get(
                        "bitrate", 0))[-1]["url"]
                else:
                    med_url = entity["media_url_https"]
                med_name = med_url.split('/')[-1].split("?tag=")[0]
                if med_name not in medids:
                    medids.add(med_name)
                    media_types.append(entity["type"])
                    media_urls.append(med_url.split("?tag=")[0])
                    media_files.append("%s_%s" % (source_id, med_name))
            else:
                normalized = normalize(entity["expanded_url"])
                links.add(normalized)
        for hashtag in tweet['entities'].get('hashtags', []):
            hashtags.add(hashtag['text'].lower())
        for mention in tweet['entities'].get('user_mentions', []):
            mentions[mention['screen_name'].lower()] = mention['id_str']
    timestamp_utc, local_time = get_dates(tweet, locale)
    text = unescape_html(text)
    tw = {
        '_id': tweet['id_str'],
        'local_time': local_time,
        'timestamp_utc': timestamp_utc,
        'text': text,
        'url': "https://twitter.com/%s/statuses/%s" % (tweet['user']['screen_name'], tweet['id_str']),
        'quoted_id': qti,
        'quoted_user': qtu,
        'quoted_user_id': qtuid,
        'quoted_timestamp_utc': qtime,
        'retweeted_id': rti,
        'retweeted_user': rtu,
        'retweeted_user_id': rtuid,
        'retweeted_timestamp_utc': rtime,
        "media_files": media_files,
        'media_types': media_types,
        'media_urls': media_urls,
        'links': sorted(links),
        'links_to_resolve': len(links) > 0,
        'hashtags': sorted(hashtags) if hashtags else process_extract(text, "#"),
        'mentioned_ids': [mentions[m] for m in sorted(mentions.keys())],
        'mentioned_names': sorted(mentions.keys()) if mentions else process_extract(text, "@"),
        'collection_time': datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f'),
        'collected_via': [tweet["gazouilloire_source"]],
        'match_query': tweet["gazouilloire_source"] != "thread" and tweet["gazouilloire_source"] != "quote"
    }

    if not tw["text"]:
        log.warning("no text for tweet %s" % tw["url"])
    tw = grab_extra_meta(tweet, tw, locale)
    results.append(tw)
    return results


def clean_user_entities(user_data):
    if 'entities' in user_data:
        for k in user_data['entities']:
            if 'urls' in user_data['entities'][k]:
                for url in user_data['entities'][k]['urls']:
                    if not url['expanded_url']:
                        continue
                    try:
                        user_data[k] = user_data[k].replace(
                            url['url'], url['expanded_url'])
                    except:
                        log.warning("couldn't process entity",
                              url, k, user_data[k])
        user_data.pop('entities')
    if 'status' in user_data:
        user_data.pop('status')
    user_data["_id"] = user_data["id"]
    return user_data
