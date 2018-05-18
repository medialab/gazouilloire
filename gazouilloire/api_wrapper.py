#/usr/bin/env python
# -*- coding: utf-8 -*-

import json
from time import time, sleep
from twitter import Twitter, OAuth, OAuth2, TwitterHTTPError

class TwitterWrapper(object):

    MAX_TRYOUTS = 5

    def __init__(self, api_keys):
        self.oauth = OAuth(api_keys['OAUTH_TOKEN'], api_keys['OAUTH_SECRET'], api_keys['KEY'], api_keys['SECRET'])
        self.oauth2 = OAuth2(bearer_token=json.loads(Twitter(api_version=None, format="", secure=True, auth=OAuth2(api_keys['KEY'], api_keys['SECRET'])).oauth2.token(grant_type="client_credentials"))['access_token'])
        self.api = {
            'user': Twitter(auth=self.oauth),
            'app': Twitter(auth=self.oauth2)
        }
        self.waits = {}

    def call(self, route, args={}, tryouts=MAX_TRYOUTS, auth='user'):
        try:
            return self.api[auth].__getattr__("/".join(route.split('.')))(**args)
        except TwitterHTTPError as e:
            if e.e.code == 429:
                reset = int(e.e.headers["x-rate-limit-reset"])
                if route not in self.waits:
                    self.waits[route] = reset
                else:
                    self.waits[route] = min(reset, self.waits[route])
                if auth == 'user':
                    return self.call(route, args, auth='app')
                sleeptime = max(int(self.waits[route] - time() - 10), 0) + 10
                print "REACHED API LIMITS on %s %s %s, will wait for the next %ss" % (route, auth, args, sleeptime)
                sleep(sleeptime)
                return self.call(route, args, tryouts, auth=('app' if auth == 'user' else 'user'))
            elif tryouts:
                return self.call(route, args, tryouts-1, auth)
            else:
                print "ERROR after %s tryouts for %s %s %s" % (self.MAX_TRYOUTS, route, auth, args)
                print "%s: %s" % (type(e), e)

