import os
import sys
import json
from elasticsearch import Elasticsearch, helpers, exceptions
import itertools


try:
    with open(os.path.join(os.path.dirname(__file__), "db_mappings.json"), "r") as db_mappings:
        DB_MAPPINGS = json.loads(db_mappings.read())
        # ensure intended mappings are there
        for key in ["tweet", "link"]:
            DB_MAPPINGS[key + "s_mapping"]["mappings"]["properties"]
except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
    print("ERROR - Could not open db_mappings.json: %s %s" % (type(e), e))
    sys.exit(1)


def reformat_elastic_document(doc):
    res = dict(doc["_source"])
    res["_id"] = doc["_id"]
    return res


def chunks(iterator, n):
    """
    generates chunks/batches of size n from an iterator
    """
    for first in iterator:
        yield itertools.chain([first], itertools.islice(iterator, n - 1))


def add_and_report(sett, val):
    """
    Add val to sett and check if val was already part of sett
    :param sett: set of tweet ids
    :param val: new tweet id
    :return: bool
    """
    leng = len(sett)
    sett.add(val)
    return len(sett) != leng


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


def prepare_db(host, port, db_name):
    try:
        db = ElasticManager(host, port, db_name)
        db_exists = db.exists(db.tweets)
    except Exception as e:
        sys.stderr.write(
            "ERROR: Could not initiate connection to database: %s %s" % (type(e), e))
        sys.exit(1)
    if db_exists:
        return db
    else:
        sys.stderr.write(
            "ERROR: elasticsearch index %s does not exist" % db_name
        )

class ElasticManager:

    def __init__(self, host, port, db_name, links_index=None):
        self.host = host
        self.port = port
        self.db_name = db_name.replace(" ", "_")
        self.client = Elasticsearch(host + ":" + str(port))
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
        return self.client.indices.exists(index=doc_type)

    def prepare_indices(self):
        """
        Check if indices exist, if not, create them
        """
        if not self.exists(self.tweets):
            self.client.indices.create(
                index=self.tweets, body=DB_MAPPINGS["tweets_mapping"])
        if not self.exists(self.links):
            self.client.indices.create(
                index=self.links, body=DB_MAPPINGS["links_mapping"])

    def delete_index(self, doc_type):
        """
        Check if index exists, if so, delete it
        """
        index_name = getattr(self, doc_type)
        if self.exists(index_name):
            self.client.indices.delete(index=index_name)
            return True
        return False

    # depiler() methods

    def update(self, tweet_id, new_value):
        """Updates the given tweet to the content of 'new_value' argument"""
        formatted_new_value = format_tweet_fields(new_value)
        return self.client.update(index=self.tweets, id=tweet_id,
                                  body={"doc": formatted_new_value, "doc_as_upsert": True})

    def prepare_indexing_links(self, links):
        """Yields an indexing action for every link of a list"""
        for l in links:
            yield {
                '_index': self.links,
                "_op_type": "index",
                '_source': l
            }

    def prepare_indexing_tweets(self, tweets):
        """Yields an indexing action for every tweet of a list. For existing tweets, only some fields are updated."""
        for t in tweets:
            reply_count = t.get("reply_count", None)
            if reply_count is not None:
                source = "ctx._source.match_query |= params.match_query; \
                    ctx._source.retweet_count = params.retweet_count; \
                    ctx._source.reply_count = params.reply_count; \
                    ctx._source.favorite_count = params.favorite_count; \
                    if (!ctx._source.collected_via.contains(params.collected_via)){ctx._source.collected_via.add(params.collected_via)}"
            else:
                source = "ctx._source.match_query |= params.match_query; \
                    ctx._source.retweet_count = params.retweet_count; \
                    ctx._source.favorite_count = params.favorite_count; \
                    if (!ctx._source.collected_via.contains(params.collected_via)){ctx._source.collected_via.add(params.collected_via)}"
            yield {
                '_index': self.tweets,
                "_op_type": "update",
                "_id": t.pop("_id"),
                "script": {
                    "source": source,
                    "lang": "painless",
                    "params": {
                        "collected_via": t["collected_via"][0],
                        "match_query": t["match_query"],
                        "retweet_count": t["retweet_count"],
                        "reply_count": reply_count,
                        "like_count": t["like_count"],
                    }

                },
                "upsert": t
            }

    def prepare_updating_links_in_tweets(self, links):
        """Yields an update action for the links of every tweet in the list"""
        for l in links:
            l.update({
                "_index": self.tweets,
                "_op_type": "update"
            })
            yield l

    def stream_tweets_batch(self, tweets, upsert=False, common_update=None):
        """Yields an update action for every tweet of a list"""
        for tweet in tweets:
            if common_update:
                doc = common_update
            else:
                doc = format_tweet_fields(tweet)
            yield {
                "_id": tweet["_id"],
                "_index": self.tweets,
                "_op_type": "update",
                "_source": {
                    "doc": doc,
                    "doc_as_upsert": upsert
                }
            }

    def set_deleted(self, tweet_id):
        """Sets the field 'deleted' of the given tweet to True"""
        return self.client.update(index=self.tweets, id=tweet_id,
                                  body={"doc": {"deleted": True}, "doc_as_upsert": True})

    def find_tweet(self, tweet_id):
        """Returns the tweet corresponding to the given id"""
        try:
            response = self.client.get(
                index=self.tweets,
                id=tweet_id
            )
        except exceptions.NotFoundError:
            return None
        return response

    def get_urls(self, url_list):
        """Returns the urls corresponding to the given url_list.
            this method is designed to replace find_links_in when the url will become the _id in elasticsearch db
        """
        response = self.client.mget(
            index=self.links,
            doc_type="link",
            body={'ids': url_list}
        )
        return response

    # resolver() methods

    def find_tweets_with_unresolved_links(self, batch_size=600):
        """Returns a list of tweets where 'links_to_resolve' field is True"""
        response = self.client.search(
            index=self.tweets,
            body={
                "_source": ["links", "proper_links", "retweet_id"],
                "size": batch_size,
                "query": {
                    "match": {
                        "links_to_resolve": True
                    }
                }
            }
        )
        return format_response(response)

    def find_links_in(self, urls_list, batch_size):
        """Returns a list of links which ids are in the 'urls_list' argument"""
        response = self.client.search(
            index=self.links,
            size=batch_size,
            body={
              "query": {
                "bool": {
                  "filter": {
                    "terms": {
                      "link_id": urls_list

                    }
                  }
                }
              }
            }
        )

        return format_response(response)

    def insert_link(self, link, resolved_link):
        """Inserts the given link in the database"""
        self.client.index(index=self.links,
                          body={"link_id": link, "real": resolved_link})

    def prepare_indexing_tweets_with_new_links(self, tweets, links, domains):
        for t in tweets:
            t["_source"]["proper_links"] = links
            t["_source"]["domains"] = domains
            t["_source"]["links_to_resolve"] = False
            yield {
                '_index': self.tweets,
                "_op_type": "index",
                '_source': t["_source"],
                "_id": t["_id"]
            }

    def update_retweets_with_links(self, tweet_id, links, domains):
        """Adds the resolved links to the corresponding tweets"""
        query = {
            "term": {
                "retweet_id": tweet_id
            }
        }
        response = helpers.scan(
            client=self.client,
            index=self.tweets,
            query={"query": query}
        )

        helpers.bulk(self.client, actions=self.prepare_indexing_tweets_with_new_links(response, links, domains))

    def count_tweets(self, key, value):
        """Counts the number of documents where the given key is equal to the given value"""
        return self.client.count(index=self.tweets, body={"query": {"term": {key: value}}})['count']

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
        self.client.update_by_query(
            body=q, index=self.tweets)

    # export methods
    def search_thread_elements(self, ids_list):
        """
        Elasticsearch query on which get_thread_ids_from_ids is based
        """
        body = {
            "_source": "to_tweetid",
            "query": {
                "bool": {
                    "filter": [{
                        "bool": {
                            "should": [
                                {"terms": {"_id": ids_list}},
                                {"terms": {"to_tweetid": ids_list}}
                            ]
                        }
                    }]
                }
            }
        }
        response = helpers.scan(
            client=self.client,
            index=self.tweets,
            query=body
        )
        return response

    def get_thread_ids_from_ids(self, ids):
        """
        Find ids of all tweets that are part of the same conversations as the tweets in ids
        :param ids: list of tweet ids
        :return:
        """
        ids_list = list(set(ids))
        all_ids = set(ids)
        while ids_list:
            todo_ids = set()
            for t in self.search_thread_elements(ids_list):
                if add_and_report(all_ids, t["_id"]):
                    todo_ids.add(t["_id"])
                origin = t.get("to_tweetid")
                if origin and add_and_report(all_ids, origin):
                    todo_ids.add(origin)
            ids_list = list(todo_ids)
        return list(all_ids)

    def multi_get(self, ids, batch_size=1000):
        for i in range(0, len(ids), batch_size):
            batch = self.client.mget(body={'ids': ids[i:i+batch_size]}, index=self.tweets)
            for tweet in batch["docs"]:
                yield tweet

if __name__ == "__main__":
    es = ElasticManager("localhost", 9200, "gazouilloire")
    es.prepare_indices()
    print(es.tweets)
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
