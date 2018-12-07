# Code adapted from Alexandr Shurigin's code on https://github.com/phpdude/python-urlsresolver under license GPLv3

# coding=utf-8
from builtins import str
from builtins import next
try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse
try:
    from html import unescape
except ImportError:
    try:
        from html.parser import HTMLParser
    except ImportError:
        from HTMLParser import HTMLParser
    parser = HTMLParser()
    unescape = parser.unescape
import re
from contextlib import closing
from collections import OrderedDict

__version__ = (1, 2, 0)

# HTML tags syntax http://www.w3.org/TR/html-markup/syntax.html
TAG_ATTRIBUTES_REGEX = \
    r"(?:\s+%(attr)s\s*=\s*\"%(dqval)s\")|" \
    r"(?:\s+%(attr)s\s*=\s*'%(sqval)s')|" \
    r"(?:\s+%(attr)s\s*=\s*%(uqval)s)|" \
    r"(?:\s+%(attr)s)" % {
        'attr': r"([^\s\x00\"'>/=]+)",
        'uqval': r"([^\s\"'=><`]*)",
        'sqval': r"([^'\x00]*)",
        'dqval': r"([^\"\x00]*)"
    }


def get_tags(html_content, tag_name):
    for m in re.findall(r'<%s(\s+[^>]*)/*>' % tag_name, html_content, re.IGNORECASE):
        attrs = {}

        for x in re.findall(r'(?:(%s))' % TAG_ATTRIBUTES_REGEX, m, re.UNICODE):
            if x[1]:
                attrs[x[1]] = unescape(x[2])
            elif x[3]:
                attrs[x[3]] = unescape(x[4])
            elif x[5]:
                attrs[x[5]] = unescape(x[6])
            elif x[7]:
                attrs[x[7]] = unescape(x[7])

        yield attrs


def resolve_url(
        start_url,
        user_agent=False,
        chunk_size=1500,
        max_redirects=30,
        history=False,
        remove_noscript=False,
        **kwargs):
    """
    Helper function for expanding shortened urls.

    :param start_url: Shortened url to expand
    :param user_agent: Custom User-Agent header.
    :param chunk_size: Size of header to fetch from response body for searching meta refresh tags.
    :param max_redirects: Maximum meta refresh redirects
    :param history: If True, function will return tuple with (url, history) where history is list of redirects
    :param remove_noscript: Remove <noscript></noscript> blocks from head HTML (skip redirects for old browsers versions)
    :param kwargs: Custom kwargs for requests.get(**kwargs) function.
    :return: str|tuple
    """
    import requests
    from requests.packages import chardet

    s = requests.session()

    urls_history = OrderedDict()
    # disable compression for streamed requests.
    s.headers['Accept-Encoding'] = ''

    if user_agent:
        s.headers['User-Agent'] = user_agent

    def follow_meta_redirects(url, redirects, **kwargs):
        urls_history[url] = True

        if redirects < 0:
            raise ValueError(
                "Cannot resolve real url with max_redirects=%s" % max_redirects)

        redirects -= 1

        with closing(s.get(url, allow_redirects=True, stream=True, **kwargs)) as resp:
            if resp.history:
                for r in resp.history:
                    urls_history[r.url] = True

            head, real_url = next(resp.iter_content(chunk_size)), resp.url

            encoding = resp.encoding
            if encoding is None:
                # detect encoding
                encoding = chardet.detect(head)['encoding']

            try:
                head = str(head, encoding, errors='replace')
            except (LookupError, TypeError):
                head = str(head, errors='replace')

        # Removing html blocks in <noscript></noscript>
        if remove_noscript:
            head = re.sub(
                r'<noscript[^>]*>.*</noscript[^>]*>', '', head, flags=re.DOTALL)

        redirect = None
        if 'refresh' in resp.headers:
            redirect = resp.headers['refresh']
        elif not redirect:
            for tag in get_tags(head, 'meta'):
                if tag.get('http-equiv', '') == 'refresh':
                    redirect = tag.get('content', None)

        if redirect:
            m = re.search(r'url\s*=\s*([^\s;]+)', redirect, re.I)
            if m:
                m = m.group(1)

                # fixing case url='#url here#'
                if m.startswith(('"', "'")) and m.endswith(('"', "'")):
                    m = m[1:-1]

                real_url = follow_meta_redirects(
                    urlparse.urljoin(resp.url, m), redirects)

        urls_history[real_url] = True

        return real_url

    real_url = follow_meta_redirects(start_url, max_redirects, **kwargs)
    if history:
        return real_url, list(urls_history.keys())
    else:
        return real_url
