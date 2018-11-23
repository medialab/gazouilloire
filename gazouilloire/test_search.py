#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
import sys
import json
from twitter import Twitter, OAuth
from run import format_keyword
from tweets import prepare_tweet
from pytz import timezone, all_timezones

try:
    with open('config.json') as confile:
        conf = json.loads(confile.read())
    oauth = OAuth(conf['twitter']['oauth_token'], conf['twitter']
                  ['oauth_secret'], conf['twitter']['key'], conf['twitter']['secret'])
    t = Twitter(auth=oauth)
except Exception as e:
    sys.exit(
        'ERROR: Could not initiate connections to Twitter API: %s %s\n' % (type(e), e))
try:
    locale = timezone(conf['timezone'])
except:
    sys.stderr.write('ERROR %s' % "\t".join(all_timezones)+"\n\n")
    sys.exit('ERROR: Unknown timezone set in config.json: %s. Please choose one among the above ones.' %
             conf['timezone'])

query = format_keyword(sys.argv[1])
print("Querying « %s »:\n" % query)
for t in t.search.tweets(q=query, count=20, include_entities='true', result_type='recent', tweet_mode='extended')['statuses']:
    pt = prepare_tweet(t, locale)
    print("%s: %s  --  %s" %
          (pt['user_screen_name'], pt['text'].replace('\n', ' '), pt["url"]))
