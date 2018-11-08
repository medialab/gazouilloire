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


class ElasticManager:
    def __init__(self, host, port, db):
        with open(os.path.dirname(os.path.realpath(__file__)) + '/db_list.json') as db_list:
            DB_LIST = json.loads(db_list.read())['db_list']
            if db not in DB_LIST:
                DB_LIST.append(db)
                json.dump(DB_LIST, db_list, indent=2)
            else:
                print('INFO -', "Using the existing '" + db + "'", 'database.')
        self.host = host
        self.port = port
        self.db = Elasticsearch(host + ':' + str(port))
        self.tweets = db + "_tweets"
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

    def find_tweets_with_unresolved_tweets(self):
        """Returns a list of tweets where 'links_to_resolve' field is True"""
        # return index.find({"links_to_resolve": True}, projection={
        #     "links": 1, "proper_links": 1, "retweet_id""retweet_id": 1}, limit=600, sort=[("_id", 1)])
        response = self.db.search(
            index=self.tweets,
            body={
                "_source": ["links", "proper_links", "retweet_id"],
                "size": 600,
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


if __name__ == '__main__':

    es = ElasticManager('localhost', 9200, 'test')
    es.prepare_indices()
    todo = es.find_tweets_with_unresolved_tweets()
    print('>> todo : ', todo[:10])
    urlstoclear = list(set([l for t in todo if not t.get(
        "proper_links", []) for l in t.get('links', [])]))
    print('>> urlstoclear : ', urlstoclear[:10])
    alreadydone = [{l["_id"]: l["real"]
                    for l in es.find_already_resolved_links(urlstoclear)}]
    print('>> alreadydone : ', alreadydone[:10])
