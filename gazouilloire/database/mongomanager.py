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

    def update(self, tweet_id,  new_value):
        coll = self.db['tweets']
        return coll.update({'_id': tweet_id}, {'$set': new_value}, upsert=True)

    def set_deleted(self, tweet_id):
        coll = self.db['tweets']
        return coll.update({'_id': tweet_id}, {'$set': {'deleted': True}}, upsert=True)

    def find_one(self, tweet_id):
        return self.db['tweets'].find_one({"_id": tweet_id})

db = MongoManager('localhost', 27017, 'py3')
print(db)


