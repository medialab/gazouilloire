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

re_entities = re.compile(r'&([^;]+);')


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


def get_timestamp(t, locale, field='created_at'):
    tim = datetime.strptime(t[field], '%a %b %d %H:%M:%S +0000 %Y')
    if locale:
        utc_date = timezone('UTC').localize(tim)
        locale_date = utc_date.astimezone(locale)
        return time.mktime(locale_date.timetuple())
    return tim.isoformat()


def nostr_field(f): return f.replace('_str', '')


def grab_extra_meta(source, result, locale=None):
    for meta in ["in_reply_to_status_id_str", "in_reply_to_screen_name", "in_reply_to_user_id_str", "lang", "geo", "coordinates", "source", "truncated", "possibly_sensitive", "withheld_copyright", "withheld_scope", "withheld_countries", "retweet_count", "favorite_count", "reply_count"]:
        if meta in source:
            result[meta] = source[meta]
        elif nostr_field(meta) in source:
            result[meta] = str(source[nostr_field(meta)])
    for meta in ['id_str', 'screen_name', 'name', 'friends_count', 'followers_count', 'statuses_count', 'favourites_count', 'listed_count', 'profile_image_url', 'location', 'verified', 'description', 'profile_image_url_https', 'utc_offset', 'time_zone', 'lang', 'withheld_scope', 'withheld_countries', 'created_at']:
        key = "user_%s" % meta.replace('_count', '')
        if key in source:
            result[key] = source[key]
        elif nostr_field(key) in source:
            result[key] = str(source[nostr_field(key)])
        elif 'user' in source and meta in source['user']:
            result[key] = source['user'][meta]
        elif 'user' in source and nostr_field(meta) in source['user']:
            result[key] = source['user'][nostr_field(meta)]
    try:
        result['user_url'] = source['user']['entities']['url']['urls'][0]['expanded_url']
    except:
        try:
            result['user_url'] = source['user']['url']
        except:
            pass
    try:
        result['user_created_at_timestamp'] = get_timestamp(
            result, locale, 'user_created_at')
    except:
        pass

    result['langs'] = [result.get('lang', '').lower()]
    return result


def prepare_tweets(tweets, locale):
    for tweet in tweets:
        if not isinstance(tweet, dict):
            continue
        if "_id" not in tweet:
            tweet = prepare_tweet(tweet, locale=locale)
        yield tweet


def prepare_tweet(tweet, locale=None):
    if "extended_tweet" in tweet:
        for field in tweet["extended_tweet"]:
            tweet[field] = tweet["extended_tweet"][field]
    text = tweet.get('full_text', tweet.get('text', ''))
    if not text:
        print("WARNING, no text for tweet %s" % "https://twitter.com/%s/statuses/%s" %
              (tweet['user']['screen_name'], tweet['id_str']))
    rti = None
    rtu = None
    rtuid = None
    rtime = None
    if "retweeted_status" in tweet and tweet['retweeted_status']['id_str'] != tweet['id_str']:
        rti = tweet['retweeted_status']['id_str']
        rtu = tweet['retweeted_status']['user']['screen_name']
        rtuid = tweet['retweeted_status']['user']['id_str']
        rtweet = prepare_tweet(tweet['retweeted_status'], locale=locale)
        rtime = rtweet['timestamp']
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
        qtweet = prepare_tweet(tweet['quoted_status'], locale=locale)
        if 'quoted_status_permalink' in tweet:
            qturl = tweet['quoted_status_permalink']['url']
        else:
            qturl = qtweet['url']
        qtime = qtweet['timestamp']
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
    medids = set([])
    medias = []
    links = set([])
    hashtags = set([])
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
                med_name = med_url.split('/')[-1]
                if med_name not in medids:
                    medids.add(med_name)
                    medias.append(["%s_%s" % (source_id, med_name), med_url])
            else:
                links.add(entity["expanded_url"])
        for hashtag in tweet['entities'].get('hashtags', []):
            hashtags.add(hashtag['text'].lower())
        for mention in tweet['entities'].get('user_mentions', []):
            mentions[mention['screen_name'].lower()] = mention['id_str']
    tw = {
        '_id': tweet['id_str'],
        'created_at': tweet['created_at'],
        'timestamp': get_timestamp(tweet, locale),
        'text': unescape_html(text),
        'url': "https://twitter.com/%s/statuses/%s" % (tweet['user']['screen_name'], tweet['id_str']),
        'quoted_id': qti,
        'quoted_user': qtu,
        'quoted_user_id': qtuid,
        'quoted_timestamp': qtime,
        'retweet_id': rti,
        'retweet_user': rtu,
        'retweet_user_id': rtuid,
        'retweet_timestamp': rtime,
        'medias': medias,
        'links': sorted(links),
        'links_to_resolve': len(links) > 0,
        'hashtags': sorted(hashtags),
        'mentions_ids': [mentions[m] for m in sorted(mentions.keys())],
        'mentions_names': sorted(mentions.keys()),
        'collected_at_timestamp': time.time()
    }
    if "gazouilloire_source" in tweet:
        tw["collected_via_%s" % tweet["gazouilloire_source"]] = True
    if not tw["text"]:
        print("WARNING, no text for tweet %s" % tw["url"])
    tw = grab_extra_meta(tweet, tw, locale)
    return tw


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
                        print("WARNING, couldn't process entity",
                              url, k, user_data[k])
        user_data.pop('entities')
    if 'status' in user_data:
        user_data.pop('status')
    user_data["_id"] = user_data["id"]
    return user_data
