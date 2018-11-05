from elasticsearch import Elasticsearch
from elasticsearch import helpers
import json
import sys
import os


class ElasticManager:
    def __init__(self, host, port, db):
        self.host = host
        self.port = port
        self.index_name = db
        self.es = Elasticsearch(host + ':' + str(port))
        if not self.es.indices.exists(index=db):
            try:
                with open(os.path.dirname(os.path.realpath(__file__)) + '/elasticsearch_mapping.json') as mappingfile:
                    mapping = json.loads(mappingfile.read())
                    self.es.indices.create(index=db, body=mapping)
            except FileNotFoundError as e:
                print(
                    'ERROR -', 'Could not open elasticsearch_mapping.json: %s %s' % (type(e), e))
                sys.exit(1)

    def update(self, tweet_id,  new_value):
        return self.es.update(index=self.index_name, doc_type='tweet', id=tweet_id, body={"doc": new_value, "doc_as_upsert": True})
        # {'_id': tweet_id}, {'$set': new_value}, upsert=True

    def set_deleted(self, tweet_id):
        return self.es.update(index=self.index_name, doc_type='tweet', id=tweet_id, body={"doc": {"deleted": True}, "doc_as_upsert": True})

    def find_one(self, tweet_id):
        return self.es.search(
            index="tweets",
            body={
                "query":
                    {
                        "match": {
                            "_id": tweet_id
                        }
                    }
            }
        )['hits']['hits'][0]['_source']
        # return self.db['tweets'].find_one({"_id": search_parameter})


es = ElasticManager('localhost', 9200, 'tweets')
print(es)

