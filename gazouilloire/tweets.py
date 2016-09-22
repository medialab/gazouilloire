# -*- coding: utf-8 -*-

import re, time
from htmlentitydefs import name2codepoint
from pytz import timezone
from datetime import datetime

re_entities = re.compile(r'&([^;]+);')
def decode_entities(x):
    if x.group(1).startswith('#'):
        return unichr(int(x.group(1)[1:]))
    try:
        return unichr(htmlentitydefs.name2codepoint[x.group(1)])
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

nostr_field = lambda f: f.replace('_str', '')

def grab_extra_meta(source, result):
    for meta in ["in_reply_to_status_id_str", "in_reply_to_screen_name", "in_reply_to_user_id_str", "lang", "geo", "coordinates", "source", "truncated", "possibly_sensitive", "withheld_copyright", "withheld_scope", "withheld_countries", "retweet_count", "favorite_count"]:
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
        result['user_created_at_timestamp'] = get_timestamp(result, locale, 'user_created_at')
    except:
        pass
    return result

def prepare_tweets(tweets, locale):
    tosave = []
    for tweet in tweets:
        if not isinstance(tweet, dict):
            continue
        tw = prepare_tweet(tweet, locale)
        tosave.append(tw)
    return tosave

def prepare_tweet(tweet, locale=None):
    if "extended_tweet" in tweet:
        for field in tweet["extended_tweet"]:
            tweet[field] = tweet["extended_tweet"][field]
    text = tweet.get('full_text', tweet['text'])
    rti = None
    rtu = None
    if "retweeted_status" in tweet and tweet['retweeted_status']['id_str'] != tweet['id_str']:
        text = "RT @%s: %s" % (tweet['retweeted_status']['user']['screen_name'], tweet['retweeted_status'].get('full_text', tweet['retweeted_status']['text']))
        rti = tweet['retweeted_status']['id_str']
        rtu = tweet['retweeted_status']['user']['screen_name']
    medias = []
    links = []
    if 'entities' in tweet or 'extended_entities' in tweet:
        source_id = rti or tweet['id_str']
        for entity in tweet.get('extended_entities', tweet['entities']).get('media', []) + tweet['entities'].get('urls', []):
            if 'expanded_url' in entity and 'url' in entity and entity['expanded_url']:
                try:
                    text = text.replace(entity['url'], entity['expanded_url'])
                except:
                    pass
            if "media_url" in entity:
                if "video_info" in entity:
                    med_url = sorted(entity["video_info"]["variants"], key=lambda x: x.get("bitrate", 0))[-1]["url"]
                else:
                    med_url = entity["media_url_https"]
                med_name = med_url.split('/')[-1]
                medias.append(["%s_%s" % (source_id, med_name), med_url])
            else:
                links.append(entity["expanded_url"])
    tw = {
        '_id': tweet['id_str'],
        'created_at': tweet['created_at'],
        'timestamp': get_timestamp(tweet, locale),
        'text': unescape_html(text),
        'url': "https://twitter.com/%s/statuses/%s" % (tweet['user']['screen_name'], tweet['id_str']),
        'retweet_id': rti,
        'retweet_user': rtu,
        'medias': medias,
        'links': links
    }
    tw = grab_extra_meta(tweet, tw)
    return tw

