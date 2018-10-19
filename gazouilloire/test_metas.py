#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
import sys
import json
from twitter import Twitter, TwitterStream, OAuth, OAuth2, TwitterHTTPError
from tweets import prepare_tweet
from pytz import timezone, all_timezones
from pprint import pprint

try:
    with open('config.json') as confile:
        conf = json.loads(confile.read())
    oauth = OAuth(conf['twitter']['oauth_token'], conf['twitter']
                  ['oauth_secret'], conf['twitter']['key'], conf['twitter']['secret'])
    oauth2 = OAuth2(bearer_token=json.loads(Twitter(api_version=None, format="", secure=True, auth=OAuth2(
        conf['twitter']['key'], conf['twitter']['secret'])).oauth2.token(grant_type="client_credentials"))['access_token'])
    t1 = Twitter(domain="api.twitter.com", api_version="1.1",
                 format="json", auth=oauth, secure=True)
    t2 = Twitter(domain="api.twitter.com", api_version="1.1",
                 format="json", auth=oauth2, secure=True)
except Exception as e:
    sys.exit(
        'ERROR: Could not initiate connections to Twitter API: %s %s\n' % (type(e), e))
try:
    locale = timezone(conf['timezone'])
except:
    sys.stderr.write('ERROR %s' % "\t".join(all_timezones)+"\n\n")
    sys.exit('ERROR: Unknown timezone set in config.json: %s. Please choose one among the above ones.' %
             conf['timezone'])

t = t1.statuses.show(
    _id=sys.argv[1], include_entities=True, tweet_mode="extended")
pprint(t)
pprint(prepare_tweet(t, locale))
