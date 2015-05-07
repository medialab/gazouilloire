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

def get_timestamp(t, locale):
    utc_date = timezone('UTC').localize(datetime.strptime(t['created_at'], '%a %b %d %H:%M:%S +0000 %Y'))
    locale_date = utc_date.astimezone(locale)
    return time.mktime(locale_date.timetuple())

nostr_field = lambda f: f.replace('_str', '')

def grab_extra_meta(source, result):
    for meta in ["in_reply_to_status_id_str", "in_reply_to_screen_name", "in_reply_to_user_id_str", "lang", "geo", "coordinates", "source"]:
        if meta in source:
            result[meta] = source[meta]
        elif nostr_field(meta) in source:
            result[meta] = str(source[nostr_field(meta)])
    for meta in ['id_str', 'screen_name', 'name', 'friends_count', 'followers_count', 'statuses_count', 'listed_count', 'profile_image_url', 'location']:
        key = "user_%s" % meta.replace('_count', '')
        if key in source:
            result[key] = source[key]
        elif nostr_field(key) in source:
            result[key] = str(source[nostr_field(key)])
        elif 'user' in source and meta in source['user']:
            result[key] = source['user'][meta]
        elif 'user' in source and nostr_field(meta) in source['user']:
            result[key] = source['user'][nostr_field(meta)]
    return result

def prepare_tweets(tweets, locale):
    tosave = []
    for tweet in tweets:
        if not isinstance(tweet, dict):
            continue
        if "retweeted_status" in tweet and tweet['retweeted_status']['id_str'] != tweet['id_str']:
            text = "RT @%s: %s" % (tweet['retweeted_status']['user']['screen_name'], tweet['retweeted_status']['text'])
        else:
            text = tweet['text']
        if 'entities' in tweet:
            for entity in tweet['entities'].get('media', []) + tweet['entities'].get('urls', []):
                if 'expanded_url' in entity and 'url' in entity and entity['expanded_url']:
                    try:
                        text = text.replace(entity['url'], entity['expanded_url'])
                    except:
                        pass
        tw = {'_id': tweet['id_str'],
              'created_at': tweet['created_at'],
              'timestamp': get_timestamp(tweet, locale),
              'text': unescape_html(text),
              'url': "https://twitter.com/%s/statuses/%s" % (tweet['user']['screen_name'], tweet['id_str'])}
        tw = grab_extra_meta(tweet, tw)
        tosave.append(tw)
    return tosave

