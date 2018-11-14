from elasticsearch import Elasticsearch
from elasticsearch import helpers
import json
import sys
import os

try:
    with open(os.path.dirname(os.path.realpath(__file__)) + '/db_mappings.json', 'r') as db_mappings:
        DB_MAPPINGS = json.loads(db_mappings.read())
except FileNotFoundError as e:
    print('ERROR -', 'Could not open db_mappings.json: %s %s' % (type(e), e))
    sys.exit(1)


def format_response(response):
    """Formats the ES find() response into a list of dictionaries"""
    if response['hits']['total'] == 0:
        return None
    result = []
    for element in response['hits']['hits']:
        # print("ELEMENT : ", element)
        result_element = {}
        result_element['_id'] = element['_id']
        for key, value in element['_source'].items():
            result_element[key] = value
        result.append(result_element)
    return result

def format_tweet_fields(tweet):
    """Adapts the fields of the given tweet to fit the index mapping"""
    try:
        user_created_at_timestamp = tweet['user_created_at_timestamp']
    except:
        user_created_at_timestamp = None
    try:
        possibly_sensitive = tweet['possibly_sensitive']
    except:
        possibly_sensitive = None
    try:
        reply_count = tweet['reply_count']
    except:
        reply_count = None
    try:
        coordinates = tweet['coordinates']['coordinates']
    except:
        coordinates = tweet['coordinates']
    try:
        proper_links = tweet['proper_links']
    except:
        proper_links = None
    try:
        collected_via_search = tweet['collected_via_search']
    except:
        collected_via_search = None
    res = {
            "collected_at_timestamp": tweet['collected_at_timestamp'],
            "collected_via_search": collected_via_search,
            "coordinates": coordinates,
            "created_at": tweet['created_at'],
            "deleted": False,
            "favorite_count": tweet['favorite_count'],
            "hashtags": tweet['hashtags'],
            "in_reply_to_screen_name": tweet['in_reply_to_screen_name'],
            "in_reply_to_status_id_str": tweet['in_reply_to_status_id_str'],
            "in_reply_to_user_id_str": tweet['in_reply_to_user_id_str'],
            "lang": tweet['lang'],
            "langs": tweet['langs'],
            "links": tweet['links'],
            "links_to_resolve": tweet['links_to_resolve'],
            "medias": tweet['medias'],
            "mentions_ids": tweet['mentions_ids'],
            "mentions_names": tweet['mentions_names'],
            "possibly_sensitive": possibly_sensitive,
            "proper_links": proper_links,
            "quoted_id": tweet['quoted_id'],
            "quoted_timestamp": tweet['quoted_timestamp'],
            "quoted_user": tweet['quoted_user'],
            "quoted_user_id": tweet['quoted_user_id'],
            "reply_count": reply_count,
            "retweet_count": tweet['retweet_count'],
            "retweet_id": tweet['retweet_id'],
            "retweet_timestamp": tweet['retweet_timestamp'],
            "retweet_user": tweet['retweet_user'],
            "retweet_user_id": tweet['retweet_user_id'],
            "source": tweet['source'],
            "text": tweet['text'],
            "timestamp": int(tweet['timestamp']),
            "truncated": tweet['truncated'],
            "tweet_id": tweet['_id'],
            "url": tweet['url'],
            "user_created_at": tweet['user_created_at'],
            "user_created_at_timestamp": user_created_at_timestamp,
            "user_description": tweet['user_description'],
            "user_favourites": tweet['user_favourites'],
            "user_followers": tweet['user_followers'],
            "user_friends": tweet['user_friends'],
            "user_id_str": tweet['user_id_str'],
            "user_lang": tweet['user_lang'],
            "user_listed": tweet['user_listed'],
            "user_location": tweet['user_location'],
            "user_name": tweet['user_name'],
            "user_profile_image_url": tweet['user_profile_image_url'],
            "user_profile_image_url_https": tweet['user_profile_image_url_https'],
            "user_screen_name": tweet['user_screen_name'],
            "user_statuses": tweet['user_statuses'],
            "user_time_zone": tweet['user_time_zone'],
            "user_url": tweet['user_url'],
            "user_utc_offset": tweet['user_utc_offset'],
            "user_verified": tweet['user_verified']}
    return res


class ElasticManager:
    def __init__(self, host, port, db, links_index=None):
        self.host = host
        self.port = port
        self.db = Elasticsearch(host + ':' + str(port))
        self.tweets = db + "_tweets"
        if links_index:
            self.links = links_index
        else:
            self.links = db + "_links"

    # main() methods

    def prepare_indices(self):
        """Initializes the database"""
        if not self.db.indices.exists(index=self.tweets):
            self.db.indices.create(
                index=self.tweets, body=DB_MAPPINGS['tweets_mapping'])
        if not self.db.indices.exists(index=self.links):
            self.db.indices.create(
                index=self.links, body=DB_MAPPINGS['links_mapping'])

    # depiler() methods

    def update(self, tweet_id,  new_value):
        """Updates the given tweet to the content of 'new_value' argument"""
        formatted_new_value = format_tweet_fields(new_value)
        return self.db.update(index=self.tweets, doc_type='tweet', id=tweet_id, body={"doc": formatted_new_value, "doc_as_upsert": True})

    def set_deleted(self, tweet_id):
        """Sets the field 'deleted' of the given tweet to True"""
        return self.db.update(index=self.tweets, doc_type='tweet', id=tweet_id, body={"doc": {"deleted": True}, "doc_as_upsert": True})

    def find_tweet(self, tweet_id):
        """Returns the tweet corresponding to the given id"""
        response = self.db.search(
            index="tweets",
            body={
                "query":
                    {
                        "match": {
                            "_id": tweet_id
                        }
                    }
            }
        )
        if response['hits']['total'] == 0:
            return None
        return response['hits']['hits'][0]['_source']

    # resolver() methods

    def find_tweets_with_unresolved_links(self, batch_size=600):
        """Returns a list of tweets where 'links_to_resolve' field is True"""
        # return index.find({"links_to_resolve": True}, projection={
        #     "links": 1, "proper_links": 1, "retweet_id""retweet_id": 1}, limit=600, sort=[("_id", 1)])
        response = self.db.search(
            index=self.tweets,
            body={
                "_source": ["links", "proper_links", "retweet_id"],
                "size": batch_size,
                "sort": [
                    {"_id": "asc"}
                ],
                "query":
                    {
                        "match": {
                            "links_to_resolve": True
                        }
                }
            }
        )
        return format_response(response)

    def find_links_in(self, urls_list):
        """Returns a list of tweets which ids are in the 'urls_list' list argument"""
        response = self.db.search(
            index=self.links,
            body={
                "query":
                    {
                        "terms": {"_id": urls_list}
                    }
            }
        )
        return format_response(response)

    def insert_link(self, link, resolved_link):
        """Inserts the given link in the database"""
        self.db.index(index=self.links, doc_type='link', id=link,
                      body={'link_id': link, 'real': resolved_link})

    def update_tweets_with_links(self, tweet_id, good_links):
        """Adds the resolved links to the corresponding tweets"""
        q = {
            "script": {
                "inline": "ctx._source.proper_links="+str(good_links)+";ctx._source.links_to_resolve=false",
                "lang": "painless"
            },
            "query": {
                "bool": {
                    "should": [
                        {
                            "term": {
                                "_id": tweet_id
                            }
                        },
                        {
                            "term": {
                                "retweet_id": tweet_id
                            }
                        }
                    ]
                }
            }
        }
        self.db.update_by_query(
            body=q, doc_type='tweet', index=self.tweets)

    def count_tweets(self, key, value):
        """Counts the number of documents where the given key is equal to the given value"""
        return self.db.count(index=self.tweets, doc_type='tweet', body={"query": {"term": {key: value}}})['count']

    def update_resolved_tweets(self, tweetsdone):
        """Sets the "links_to_resolve" field of the tweets in tweetsdone to False"""
        # self.tweets.update({"_id": {"$in": tweetsdone}}, {
        #     "$set": {"links_to_resolve": False}}, upsert=False, multi=True)
        q = {
            "script": {
                "inline": "ctx._source.links_to_resolve=false",
                "lang": "painless"
            },
            "query": {
                "terms": {"_id": tweetsdone}
            }
        }
        self.db.update_by_query(
            body=q, doc_type='tweet', index=self.tweets)


if __name__ == '__main__':

    es = ElasticManager('localhost', 9200, 'test')
    es.prepare_indices()
    todo = es.find_tweets_with_unresolved_links()
    print('>> todo : ', todo[:10])
    urlstoclear = list(set([l for t in todo if not t.get(
        "proper_links", []) for l in t.get('links', [])]))
    print('>> urlstoclear : ', urlstoclear[:10])
    alreadydone = [{l["_id"]: l["real"]
                    for l in es.find_links_in(urlstoclear)}]
    print('>> alreadydone : ', alreadydone[:10])
    # es.update_tweets_with_links(
    #     1057377903506325506, ["goodlink3", "goodlink4"])
    print(es.count_tweets('retweet_id', '1057377903506325506'))
    es.update_resolved_tweets([1057223967893729280, 1057223975032373249])
