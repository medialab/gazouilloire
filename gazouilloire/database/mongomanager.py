from pymongo import ASCENDING
try:
    from pymongo import MongoClient
except:
    from pymongo import Connection as MongoClient


class MongoManager:

    link_id = "_id"

    def __init__(self, host, port, db):
        self.host = host
        self.port = port
        self.db_name = db.replace(" ", "_")
        self.db = MongoClient(host, port)[self.db_name]
        self.tweets = self.db["tweets"]
        self.links = self.db["links"]

    # main() methods

    def prepare_indices(self):
        """Initializes the database"""
        for f in ["retweet_id", "in_reply_to_status_id_str", "timestamp",
                  "links_to_resolve", "lang", "user_lang", "langs"]:
            self.tweets.create_index([(f, ASCENDING)], background=True)
        self.tweets.create_index(
            [("links_to_resolve", ASCENDING), ("_id", ASCENDING)], background=True)

    # depiler() methods

    def update(self, tweet_id, new_value):
        """Updates the given tweet to the content of 'new_value' argument"""
        return self.tweets.update_one({"_id": tweet_id}, {"$set": new_value}, upsert=True)

    def bulk_update(self, batch):
        """Updates the batch of tweets given in argument"""
        for t in batch:
            self.update(t["_id"], t)

    def set_deleted(self, tweet_id):
        """Sets the field 'deleted' of the given tweet to True"""
        return self.tweets.update_one({"_id": tweet_id}, {"$set": {"deleted": True}}, upsert=True)

    def find_tweet(self, tweet_id):
        """Returns the tweet corresponding to the given id"""
        return self.tweets.find_one({"_id": tweet_id})

    # resolver() methods

    def find_tweets_with_unresolved_links(self, batch_size=600):
        """Returns a list of tweets where 'links_to_resolve' field is True"""
        return list(self.tweets.find({"links_to_resolve": True}, projection={"links": 1, "proper_links": 1, "retweet_id": 1}, limit=batch_size, sort=[("_id", 1)]))

    def find_links_in(self, urls_list):
        """Returns a list of links which ids are in the 'urls_list' argument"""
        return list(self.links.find({self.link_id: {"$in": urls_list}}))

    def insert_link(self, link, resolved_link):
        """Inserts the given link in the database"""
        self.links.update_one(
            {self.link_id: link}, {"$set": {self.link_id: link, "real": resolved_link}}, upsert=True)

    def update_tweets_with_links(self, tweet_id, good_links):
        """Adds the resolved links to the corresponding tweets"""
        self.tweets.update_many({"$or": [{"_id": tweet_id}, {"retweet_id": tweet_id}]}, {
            "$set": {"proper_links": good_links, "links_to_resolve": False}}, upsert=False)

    def count_tweets(self, key, value):
        """Counts the number of documents where the given key is equal to the given value"""
        return self.tweets.count({key: value})

    def update_resolved_tweets(self, tweetsdone):
        """Sets the "links_to_resolve" field of the tweets in tweetsdone to False"""
        self.tweets.update({"_id": {"$in": tweetsdone}}, {
            "$set": {"links_to_resolve": False}}, upsert=False, multi=True)

    # prepare_tweets() methods


if __name__ == "__main__":

    db = MongoManager("localhost", 27017, "gazouilloire")
    db.prepare_indices()
    # todo = db.find_tweets_with_unresolved_links()
    # print(">> todo : ", todo[:10])
    # urlstoclear = list(set([l for t in todo if not t.get(
    #     "proper_links", []) for l in t.get("links", [])]))
    # print(">> urlstoclear : ", urlstoclear[:10])
    # alreadydone = [{l[db.link_id]: l["real"]
    #                 for l in db.find_links_in(urlstoclear)}]
    # print(">> alreadydone : ", alreadydone[:10])
    # print(db.count_tweets("retweet_id", "1057377903506325506"))
