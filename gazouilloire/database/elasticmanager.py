import os
import sys
import json
from copy import deepcopy
from elasticsearch import Elasticsearch
from elasticsearch import helpers
from itertools import chain, islice

try:
    with open(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))), "config.json"), "r") as confile:
        conf = json.loads(confile.read())
        analyzer = conf.get('text_analyzer', 'standard')
except Exception as e:
    print('WARNING - Could not open config.json: %s %s' % (type(e), e))
    analyzer = 'standard'

try:
    with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), "db_mappings.json"), "r") as db_mappings:
        DB_MAPPINGS = json.loads(db_mappings.read())
        # ensure intended mappings are there
        for key in ["tweet", "link"]:
            DB_MAPPINGS[key + "s_mapping"]["mappings"][key]["properties"]
except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
    print("ERROR - Could not open db_mappings.json: %s %s" % (type(e), e))
    sys.exit(1)

# updating the text analyzer according to the config.json
DB_MAPPINGS['tweets_mapping']['mappings']['tweet']['properties']['user_description']['analyzer'] = analyzer
DB_MAPPINGS['tweets_mapping']['mappings']['tweet']['properties']['text']['analyzer'] = analyzer


def reformat_elastic_document(doc):
    res = dict(doc["_source"])
    res["_id"] = doc["_id"]
    return res


def chunks(iterator, n):
    """
    generates chunks/batches of size n from an iterator
    """
    for first in iterator:
        yield chain([first], islice(iterator, n - 1))


def format_response(response, single_result=False):
    """Formats the ES find() response into a list of dictionaries"""
    if response["hits"]["total"] == 0:
        if single_result:
            return None
        return []
    if single_result:
        return reformat_elastic_document(response["hits"]["hits"][0])
    return [reformat_elastic_document(element) for element in response["hits"]["hits"]]


def format_tweet_fields(tweet):
    """Adapts the fields of the given tweet to fit the index mapping"""
    elastic_tweet = {}
    for key in DB_MAPPINGS["tweets_mapping"]["mappings"]["tweet"]["properties"]:
        elastic_tweet[key] = tweet.get(key, None)
    if not elastic_tweet["deleted"]:
        elastic_tweet["deleted"] = False
    if elastic_tweet["coordinates"]:
        elastic_tweet["coordinates"] = elastic_tweet["coordinates"].get(
            'coordinates', None)
    return elastic_tweet


class ElasticManager:

    link_id = "link_id"

    def __init__(self, host, port, db_name, links_index=None):
        self.host = host
        self.port = port
        self.db_name = db_name.replace(" ", "_")
        self.db = Elasticsearch(host + ":" + str(port))
        self.tweets = self.db_name + "_tweets"
        if links_index:
            self.links = links_index
        else:
            self.links = self.db_name + "_links"

    # main() methods

    def exists(self, doc_type):
        """
        Check if index already exists in elasticsearch
        """
        return self.db.indices.exists(index=doc_type)

    def prepare_indices(self):
        """Initializes the database"""
        if not self.exists(self.tweets):
            self.db.indices.create(
                index=self.tweets, body=DB_MAPPINGS["tweets_mapping"])
        if not self.exists(self.links):
            self.db.indices.create(
                index=self.links, body=DB_MAPPINGS["links_mapping"])

    # depiler() methods

    def update(self, tweet_id, new_value):
        """Updates the given tweet to the content of 'new_value' argument"""
        formatted_new_value = format_tweet_fields(new_value)
        return self.db.update(index=self.tweets, doc_type="tweet", id=tweet_id, body={"doc": formatted_new_value, "doc_as_upsert": True})

    def stream_links_batch(self, links):
        """Yields an index action for every link of a list"""
        for l in links:
            yield {
                '_index': self.links,
                "_op_type": "index",
                '_source': l,
                "_type": "link"
            }


    def bulk_links(self, links):
        """index the batch of links given in argument"""
        streaming_bulk = helpers.bulk(
            self.db, actions=self.stream_links_batch(links))

    def prepare_update_tweets_batch(self, links):
        """Yields an update action for every tweet of a list"""
        for l in links:
            l.update({
                "_type": "tweet",
                "_index": self.tweets,
                "_op_type": "update"
            })
            yield l

    def bulk_update_tweets(self, tweets):
        """update tweets with their new links"""
        streaming_bulk = helpers.bulk(
            self.db, actions=self.prepare_update_tweets_batch(tweets))


    def stream_tweets_batch(self, tweets, upsert=False, common_update=None):
        """Yields an update action for every tweet of a list"""
        for tweet in tweets:
            if common_update:
                doc = common_update
            else:
                doc = format_tweet_fields(tweet)
            yield {
                "_id": tweet["_id"],
                "_type": "tweet",
                "_index": self.tweets,
                "_op_type": "update",
                "_source": {
                    "doc": doc,
                    "doc_as_upsert": upsert
                }
            }

    def bulk_update_tweets(self, batch):
        """Updates the batch of tweets given in argument"""
        streaming_bulk = helpers.streaming_bulk(
            self.db, actions=self.stream_tweets_batch(batch, upsert=True))
        for ok, response in streaming_bulk:
            if not ok:
                print(response)

    def set_deleted(self, tweet_id):
        """Sets the field 'deleted' of the given tweet to True"""
        return self.db.update(index=self.tweets, doc_type="tweet", id=tweet_id, body={"doc": {"deleted": True}, "doc_as_upsert": True})

    def find_tweet(self, tweet_id):
        """Returns the tweet corresponding to the given id"""
        response = self.db.get(
            index=self.tweets,
            doc_type="tweet",
            id=tweet_id
        )
        return response

    def get_urls(self, url_list):
        """Returns the urls corresponding to the given url_list.
            this method is designed to replace find_links_in when the url will become the _id in elasticsearch db
        """
        response = self.db.mget(
            index=self.links,
            doc_type="link",
            body={'ids': url_list}
        )
        return response


    # resolver() methods

    def find_tweets_with_unresolved_links(self, batch_size=600):
        """Returns a generator of tweets where 'links_to_resolve' field is True"""
        # return index.find({"links_to_resolve": True}, projection={
        #     "links": 1, "proper_links": 1, "retweet_id""retweet_id": 1}, limit=batch_size, sort=[("_id", 1)])
        response = helpers.scan(
            client=self.db,
            index=self.tweets,
            query={
                "_source": ["links", "proper_links", "retweet_id"],
                "query": {
                    "match": {
                        "links_to_resolve": True
                    }
                }
            }
        )
        return chunks(response, batch_size)

    def find_links_in(self, urls_list):
        """Returns a list of links which ids are in the 'urls_list' argument"""
        response = self.db.search(
            index=self.links,
            body={
                "query": {
                    "terms": {self.link_id: urls_list}
                }
            }
        )
        return format_response(response)

    def insert_link(self, link, resolved_link):
        """Inserts the given link in the database"""
        self.db.index(index=self.links, doc_type="link",
                      body={self.link_id: link, "real": resolved_link})

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
        search_result = self.db.search(
            index=self.tweets,
            body={"query": query}
        )
        actions_stream = self.stream_tweets_batch(
            search_result["hits"]["hits"],
            common_update={
                "proper_links": good_links,
                "links_to_resolve": False
            }
        )
        helpers.bulk(self.db, actions=actions_stream)

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
            body=q, doc_type="tweet", index=self.tweets)


if __name__ == "__main__":

    es = ElasticManager("localhost", 9200, "gazouilloire")
    es.prepare_indices()
    # todo = es.find_tweets_with_unresolved_links()
    # print(">> todo : ", todo[:10])
    # urlstoclear = list(set([l for t in todo if not t.get(
    #     "proper_links", []) for l in t.get("links", [])]))
    # print(">> urlstoclear : ", urlstoclear[:10])
    # alreadydone = [{l["_id"]: l["real"]
    #                 for l in es.find_links_in(urlstoclear)}]
    # print(">> alreadydone : ", alreadydone[:10])
    # # es.update_tweets_with_links(
    # #     1057377903506325506, ["goodlink3", "goodlink4"])
    # print(es.count_tweets("retweet_id", "1057377903506325506"))
    # es.update_resolved_tweets([1057223967893729280, 1057223975032373249])
