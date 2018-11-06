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

    def prepare_indices(self):
        if not self.es.indices.exists(index=self.index_name):
            try:
                with open(os.path.dirname(os.path.realpath(__file__)) + '/elasticsearch_mapping.json') as mappingfile:
                    mapping = json.loads(mappingfile.read())
                    self.es.indices.create(index=self.index_name, body=mapping)
            except FileNotFoundError as e:
                print(
                    'ERROR -', 'Could not open elasticsearch_mapping.json: %s %s' % (type(e), e))
                sys.exit(1)

    def update(self, tweet_id,  new_value):
        return self.es.update(index=self.index_name, doc_type='tweet', id=tweet_id, body={"doc": new_value, "doc_as_upsert": True})

    def set_deleted(self, tweet_id):
        return self.es.update(index=self.index_name, doc_type='tweet', id=tweet_id, body={"doc": {"deleted": True}, "doc_as_upsert": True})

    def find_one(self, tweet_id):
        response = self.es.search(
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


if __name__ == '__main__':

    es = ElasticManager('localhost', 9200, 'tweets')
    es.prepare_indices()
    print(es.find_one(1057589842425589760))
