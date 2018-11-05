
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from builtins import int
from builtins import str
from builtins import bytes
from builtins import range
import json
try:
    from httplib import BadStatusLine
except ImportError:
    from http.client import BadStatusLine
try:
    from urllib2 import URLError
except ImportError:
    from urllib.error import URLError
try:
    from urllib import quote
except ImportError:
    from urllib.parse import quote
import requests
requests.packages.urllib3.disable_warnings()
from gazouilloire.url_resolver import resolve_url as resolve_redirects
from twitter import TwitterStream, OAuth

with open('config.json') as confile:
    conf = json.loads(confile.read())
oauth = OAuth(conf['twitter']['oauth_token'], conf['twitter']['oauth_secret'], conf['twitter']['key'], conf['twitter']['secret'])
StreamConn = TwitterStream(domain="stream.twitter.com", api_version="1.1", auth=oauth, secure=True, block=False, timeout=10)
args = {
    "track": quote("gaga", '')
}
for i in StreamConn.statuses.filter(**args):
    print(i)
