#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
import sys
import json
from twitter import TwitterStream, OAuth
from tweets import prepare_tweet
from pytz import timezone, all_timezones

try:
    with open('config.json') as confile:
        conf = json.loads(confile.read())
    oauth = OAuth(conf['twitter']['oauth_token'], conf['twitter']
                  ['oauth_secret'], conf['twitter']['key'], conf['twitter']['secret'])
    ts = TwitterStream(auth=oauth)
except Exception as e:
    sys.exit(
        'ERROR: Could not initiate connections to Twitter API: %s %s\n' % (type(e), e))
try:
    locale = timezone(conf['timezone'])
except:
    sys.stderr.write('ERROR %s' % "\t".join(all_timezones)+"\n\n")
    sys.exit('ERROR: Unknown timezone set in config.json: %s. Please choose one among the above ones.' %
             conf['timezone'])

query = sys.argv[1].strip().lower()
print("Querying « %s »:\n" % query)
try:
    for t in ts.statuses.filter(track=query, filter_level='none', stall_warnings='true'):
        if not t:
            continue
        if isinstance(t, dict):
            if 'id_str' in t:
                pt = prepare_tweet(t, locale)
                print("%s: %s  --  %s" %
                      (pt['user_screen_name'], pt['text'].replace('\n', ' '), pt["url"]))
            else:
                print("Special data: %s" % t)
except KeyboardInterrupt:
    pass
