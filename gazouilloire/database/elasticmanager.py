import os
import sys
import json
from copy import deepcopy
from elasticsearch import Elasticsearch
from elasticsearch import helpers


try:
    with open(os.path.join(os.path.dirname(os.path.realpath(__file__)),'db_mappings.json'), 'r') as db_mappings:
        DB_MAPPINGS = json.loads(db_mappings.read())
except (FileNotFoundError, json.JSONDecodeError) as e:
    print('ERROR -', 'Could not open db_mappings.json: %s %s' % (type(e), e))
    sys.exit(1)


def reformat_elastic_document(doc):
    res = dict(doc['_source'])
    res['_id'] = doc['_id']
    return res

def format_response(response, empty_response=None):
    """Formats the ES find() response into a list of dictionaries"""
    if response['hits']['total'] == 0:
        return empty_response
    return [reformat_elastic_document(element) for element in response['hits']['hits']]

def format_tweet_fields(tweet):
    """Adapts the fields of the given tweet to fit the index mapping"""
    elastic_tweet = {}
    for key in DB_MAPPINGS["tweets_mapping"]["mappings"]["tweet"]["properties"]:
        elastic_tweet[key] = tweet.get(key, None)
    elastic_tweet["tweet_id"] = tweet["_id"]
    if not elastic_tweet["deleted"]:
        elastic_tweet["deleted"] = False
    if elastic_tweet["coordinates"]:
        elastic_tweet["coordinates"] = elastic_tweet["coordinates"].get('coordinates', None)
    return elastic_tweet

def stream(batch, index, upsert=False):
    for t in batch:
        yield {
            '_id': t['_id'],
            "_type": "tweet",
            "_index": index,
            "_source": {"doc": format_tweet_fields(t), "doc_as_upsert": upsert},
            '_op_type': 'update'
        }


class ElasticManager:
    def __init__(self, host, port, db, links_index=None):
        self.host = host
        self.port = port
        self.db = Elasticsearch(host + ':' + str(port))
        self.tweets = db.replace(' ', '_') + "_tweets"
        if links_index:
            self.links = links_index
        else:
            self.links = db.replace(' ', '_') + "_links"
        self.link_id = "link_id"

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

    def bulk_update(self, batch):
        """Updates the batch of tweets given in argument"""
        tweet_stream = stream(batch, self.tweets, upsert=True)
        for ok, response in helpers.streaming_bulk(self.db, actions=tweet_stream):
            if not ok:
                print(response)

    def set_deleted(self, tweet_id):
        """Sets the field 'deleted' of the given tweet to True"""
        return self.db.update(index=self.tweets, doc_type='tweet', id=tweet_id, body={"doc": {"deleted": True}, "doc_as_upsert": True})

    def find_tweet(self, tweet_id):
        """Returns the tweet corresponding to the given id"""
        response = self.db.search(
            index="tweets",
            body={
                "query": {
                    "match": {
                        "_id": tweet_id
                    }
                }
            }
        )
        if response['hits']['total'] == 0:
            return None
        return reformat_elastic_document(response['hits']['hits'][0])

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
                "sort": [{"_id": "asc"}],
                "query": {
                    "match": {
                        "links_to_resolve": True
                    }
                }
            }
        )
        return format_response(response, empty_response=[])

    def find_links_in(self, urls_list):
        """Returns a list of links which ids are in the 'urls_list' argument"""
        response = self.db.search(
            index=self.links,
            body={
                "query": {
                    "terms": {"link_id": urls_list}
                }
            }
        )
        return format_response(response, empty_response=[])

    def insert_link(self, link, resolved_link):
        """Inserts the given link in the database"""
        self.db.index(index=self.links, doc_type='link',
                      body={'link_id': link, 'real': resolved_link})

    def stream_update_actions(self, query, field_update=None, upsert=False):
        """Yields an update action for every id corresponding to the search query"""
        search_result = self.db.search(
            index=self.tweets,
            body={
                "query": query
            }
        )
        for tweet in search_result['hits']['hits']:
            yield {
                '_id': tweet['_id'],
                "_type": "tweet",
                "_index": self.tweets,
                "_source": {"doc": field_update, "doc_as_upsert": upsert},
                '_op_type': 'update'
            }

    def update_tweets_with_links(self, tweet_id, good_links):
        """Adds the resolved links to the corresponding tweets"""
        query = {
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
        field_update = {"proper_links": good_links,
            "links_to_resolve": False}
        actions_stream = self.stream_update_actions(
            query, field_update=field_update, upsert=False)
        helpers.bulk(self.db, actions_stream)

    def count_tweets(self, key, value):
        """Counts the number of documents where the given key is equal to the given value"""
        return self.db.count(index=self.tweets, doc_type='tweet', body={"query": {"term": {key: value}}})['count']

    def update_resolved_tweets(self, tweetsdone):
        """Sets the "links_to_resolve" field of the tweets in tweetsdone to False"""
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

    es = ElasticManager('localhost', 9200, 'juliacage')
    es.prepare_indices()
    # todo = es.find_tweets_with_unresolved_links()
    # print('>> todo : ', todo[:10])
    # urlstoclear = list(set([l for t in todo if not t.get(
    #     "proper_links", []) for l in t.get('links', [])]))
    # print('>> urlstoclear : ', urlstoclear[:10])
    # alreadydone = [{l["_id"]: l["real"]
    #                 for l in es.find_links_in(urlstoclear)}]
    # print('>> alreadydone : ', alreadydone[:10])
    # # es.update_tweets_with_links(
    # #     1057377903506325506, ["goodlink3", "goodlink4"])
    # print(es.count_tweets('retweet_id', '1057377903506325506'))
    # es.update_resolved_tweets([1057223967893729280, 1057223975032373249])
