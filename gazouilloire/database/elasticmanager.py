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
        return self.db.update(index=self.tweets, doc_type='tweet', id=tweet_id, body={"doc": new_value, "doc_as_upsert": True})

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

    def find_already_resolved_links(self, urlstoclear):
        """Returns a list of tweets which ids are in the 'urlstoclear' list argument"""
        response = self.db.search(
            index=self.links,
            body={
                "query":
                    {
                        "terms": {"_id": urlstoclear}
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

    def count_tweets(self, parameter):
        """Counts the number of documents with the given parameter"""
        return self.db.count(index=self.tweets, doc_type='tweet', body={"query": {"term": parameter}})['count']


if __name__ == '__main__':

    es = ElasticManager('localhost', 9200, 'test')
    es.prepare_indices()
    todo = es.find_tweets_with_unresolved_links()
    print('>> todo : ', todo[:10])
    urlstoclear = list(set([l for t in todo if not t.get(
        "proper_links", []) for l in t.get('links', [])]))
    print('>> urlstoclear : ', urlstoclear[:10])
    alreadydone = [{l["_id"]: l["real"]
                    for l in es.find_already_resolved_links(urlstoclear)}]
    print('>> alreadydone : ', alreadydone[:10])
    # es.update_tweets_with_links(
    #     1057377903506325506, ["goodlink3", "goodlink4"])
    print(es.count_tweets({'retweet_id': '1057377903506325506'}))
