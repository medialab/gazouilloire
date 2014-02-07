# -*- coding: utf-8 -*-

import re, htmlentitydefs

re_entities = re.compile(r'&([^;]+);')
def unescape_html(text):
    return re_entities.sub(lambda x: unichr(int(x.group(1)[1:])) if x.group(1).startswith('#') else unichr(htmlentitydefs.name2codepoint[x.group(1)]), text)

def grab_extra_meta(source, result):
    for meta in ["in_reply_to_status_id_str", "in_reply_to_screen_name", "lang", "geo", "coordinates", "source"]:
        if meta in source:
            result[meta] = source[meta]
    for meta in ['screen_name', 'name', 'friends_count', 'followers_count', 'statuses_count', 'listed_count']:
        key = "user_%s" % meta.replace('_count', '')
        if key in source:
            result[key] = source[key]
        elif 'user' in source and meta in source['user']:
            result[key] = source['user'][meta]
    return result

def prepare_tweets(tweets):
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
              'text': unescape_html(text),
              'url': "https://twitter.com/%s/statuses/%s" % (tweet['user']['screen_name'], tweet['id_str'])}
        tw = grab_extra_meta(tweet, tw)
        tosave.append(tw)
    return tosave


