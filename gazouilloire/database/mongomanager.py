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
        self.tweets = self.db['tweets']
        self.links = self.db['links']

    # main() methods

    def prepare_indices(self):
        """Initializes the database"""
        coll = self.tweets
        for f in ['retweet_id', 'in_reply_to_status_id_str', 'timestamp',
                  'links_to_resolve', 'lang', 'user_lang', 'langs']:
            coll.create_index([(f, ASCENDING)], background=True)
        coll.create_index(
            [('links_to_resolve', ASCENDING), ('_id', ASCENDING)], background=True)

    # depiler() methods

    def update(self, tweet_id,  new_value):
        """Updates the given tweet to the content of 'new_value' argument"""
        coll = self.tweets
        return coll.update_one({'_id': tweet_id}, {'$set': new_value}, upsert=True)

    def set_deleted(self, tweet_id):
        """Sets the field 'deleted' of the given tweet to True"""
        coll = self.tweets
        return coll.update_one({'_id': tweet_id}, {'$set': {'deleted': True}}, upsert=True)

    def find_tweet(self, tweet_id):
        """Returns the tweet corresponding to the given id"""
        return self.tweets.find_one({"_id": tweet_id})

    # resolver() methods

    def find_tweets_with_unresolved_links(self, batch_size=600):
        """Returns a list of tweets where 'links_to_resolve' field is True"""
        return list(self.tweets.find({"links_to_resolve": True}, projection={"links": 1, "proper_links": 1, "retweet_id": 1}, limit=batch_size, sort=[("_id", 1)]))

    def find_already_resolved_links(self, urlstoclear):
        """Returns a list of tweets which ids are in the 'urlstoclear' list argument"""
        return list(self.links.find({"_id": {"$in": urlstoclear}}))

    def insert_link(self, link, resolved_link):
        """Inserts the given link in the database"""
        self.links.insert_one({'_id': link, 'real': resolved_link})

    def update_tweets_with_links(self, tweet_id, good_links):
        """Adds the resolved links to the corresponding tweets"""
        self.tweets.update_many({'$or': [{'_id': tweet_id}, {'retweet_id': tweet_id}]}, {
            '$set': {'proper_links': good_links, 'links_to_resolve': False}}, upsert=False)


if __name__ == '__main__':

    db = MongoManager('localhost', 27017, 'py3')
    db.prepare_indices()
    todo = db.find_tweets_with_unresolved_links()
    print('>> todo : ', todo[:10])
    urlstoclear = list(set([l for t in todo if not t.get(
        "proper_links", []) for l in t.get('links', [])]))
    print('>> urlstoclear : ', urlstoclear[:10])
    alreadydone = [{l["_id"]: l["real"]
                    for l in db.find_already_resolved_links(urlstoclear)}]
    print('>> alreadydone : ', alreadydone[:10])
