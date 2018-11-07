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
        coll = self.db['tweets']
        for f in ['retweet_id', 'in_reply_to_status_id_str', 'timestamp',
                  'links_to_resolve', 'lang', 'user_lang', 'langs']:
            coll.ensure_index([(f, ASCENDING)], background=True)
        coll.ensure_index(
            [('links_to_resolve', ASCENDING), ('_id', ASCENDING)], background=True)

    # depiler() methods

    def update(self, tweet_id,  new_value):
        coll = self.db['tweets']
        return coll.update_one({'_id': tweet_id}, {'$set': new_value}, upsert=True)

    def set_deleted(self, tweet_id):
        coll = self.db['tweets']
        return coll.update_one({'_id': tweet_id}, {'$set': {'deleted': True}}, upsert=True)

    def find_one(self, tweet_id):
        return self.db['tweets'].find_one({"_id": tweet_id})

    # resolver() methods

    def find_todo(self, index):
        # for x in self.db[index].find({"links_to_resolve": True}, projection={"links": 1, "proper_links": 1, "retweet_id": 1}, limit=600, sort=[("_id", 1)]):
        #     print(x.keys())
        return list(self.db[index].find({"links_to_resolve": True}, projection={"links": 1, "proper_links": 1, "retweet_id": 1}, limit=600, sort=[("_id", 1)]))


if __name__ == '__main__':

    db = MongoManager('localhost', 27017, 'py3')
    print(db)
    db.update(1059809701448290304,  {"links_to_resolve": True})
    print(len(db.find_todo(db.tweets)))
