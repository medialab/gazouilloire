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
        if not self.db.indices.exists(index=self.tweets):
            self.db.indices.create(
                index=self.tweets, body=DB_MAPPINGS['tweets_mapping'])
            self.db.indices.create(
                index=self.links, body=DB_MAPPINGS['links_mapping'])

    # depiler() methods

    def update(self, tweet_id,  new_value):
        return self.db.update(index=self.tweets, doc_type='tweet', id=tweet_id, body={"doc": new_value, "doc_as_upsert": True})

    def set_deleted(self, tweet_id):
        return self.db.update(index=self.tweets, doc_type='tweet', id=tweet_id, body={"doc": {"deleted": True}, "doc_as_upsert": True})

    def find_one(self, tweet_id):
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

    def find_todo(self, index):
        # return index.find({"links_to_resolve": True}, projection={
        #     "links": 1, "proper_links": 1, "retweet_id""retweet_id": 1}, limit=600, sort=[("_id", 1)])
        response = self.db.search(
            index=index,
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


if __name__ == '__main__':

    es = ElasticManager('localhost', 9200, 'test')
    es.prepare_indices()
    es.update(1059809701448290304,  {"links_to_resolve": True})
    # print(es.find_todo(es.tweets))
    print(len(es.find_todo(es.tweets)))
