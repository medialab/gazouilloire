from pymongo import ASCENDING
try:
    from pymongo import MongoClient
except:
    from pymongo import Connection as MongoClient


class MongoManager:
    def __init__(self, host, port, db):
        self.host = host
        self.port = port
        self.db_name = db
        self.db = MongoClient(host, port)[db]
        self.tweets = 'tweets'
        self.links = 'links'
    # main() methods

    def prepare_indices(self):
        """Initializes the database"""
        coll = self.db['tweets']
        for f in ['retweet_id', 'in_reply_to_status_id_str', 'timestamp',
                  'links_to_resolve', 'lang', 'user_lang', 'langs']:
            coll.create_index([(f, ASCENDING)], background=True)
        coll.create_index(
            [('links_to_resolve', ASCENDING), ('_id', ASCENDING)], background=True)

    # depiler() methods

    def update(self, tweet_id,  new_value):
        """Updates the given tweet to the content of 'new_value' argument"""
        coll = self.db['tweets']
        return coll.update_one({'_id': tweet_id}, {'$set': new_value}, upsert=True)

    def set_deleted(self, tweet_id):
        """Sets the field 'deleted' of the given tweet to True"""
        coll = self.db['tweets']
        return coll.update_one({'_id': tweet_id}, {'$set': {'deleted': True}}, upsert=True)

    def find_tweet(self, tweet_id):
        """Returns the tweet corresponding to the given id"""
        return self.db['tweets'].find_one({"_id": tweet_id})

    # resolver() methods

    def find_tweets_with_unresolved_tweets(self):
        """Returns a list of tweets where 'links_to_resolve' field is True"""
        return list(self.db[self.tweets].find({"links_to_resolve": True}, projection={"links": 1, "proper_links": 1, "retweet_id": 1}, limit=600, sort=[("_id", 1)]))

    def find_already_resolved_links(self, urlstoclear):
        """Returns a list of tweets which ids are in the 'urlstoclear' list argument"""
        return list(self.db[self.links].find({"_id": {"$in": urlstoclear}}))


if __name__ == '__main__':

    db = MongoManager('localhost', 27017, 'py3')
    db.prepare_indices()
    todo = db.find_tweets_with_unresolved_tweets()
    print('>> todo : ', todo[:10])
    urlstoclear = list(set([l for t in todo if not t.get(
        "proper_links", []) for l in t.get('links', [])]))
    print('>> urlstoclear : ', urlstoclear[:10])
    alreadydone = [{l["_id"]: l["real"]
                    for l in db.find_already_resolved_links(urlstoclear)}]
    print('>> alreadydone : ', alreadydone[:10])
