import json
from twitter import Twitter, TwitterStream, OAuth, OAuth2


def get_oauth(conf):
    twitter_conf = conf['twitter']

    oauth = OAuth(twitter_conf['oauth_token'], twitter_conf['oauth_secret'], twitter_conf['key'],
                  twitter_conf['secret'])
    if "bearer_token" in twitter_conf:
        oauth2 = OAuth2(bearer_token=twitter_conf['bearer_token'])
    else:
        oauth2 = OAuth2(bearer_token=json.loads(Twitter(api_version=None, format="", secure=True,
                                                        auth=OAuth2(twitter_conf['key'],
                                                                    twitter_conf['secret'])).oauth2.token(
            grant_type="client_credentials"))['access_token'])

    return oauth, oauth2


def instantiate_clients(oauth, oauth2):
    common_kwargs = {
        'domain': 'api.twitter.com',
        'api_version': '1.1',
        'format': 'json',
        'secure': True
    }

    search = Twitter(auth=oauth, **common_kwargs)
    search2 = Twitter(auth=oauth2, **common_kwargs)
    stream = TwitterStream(
        domain="stream.twitter.com",
        api_version="1.1",
        auth=oauth,
        secure=True,
        block=False,
        timeout=10
    )

    return search, search2, stream