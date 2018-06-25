#/usr/bin/env python
# -*- coding: utf-8 -*-

import networkx as nx
from pymongo import MongoClient
from gazouilloire.tweets import clean_user_entities
from gazouilloire.api_wrapper import TwitterWrapper


def collect_user_and_friends(user_name, api, db):
    print "- WORKING ON %s" % user_name
    if type(user_name) in (str, unicode):
        field = "screen_name"
    else:
        field = "_id"
    user = {field: user_name}
    done_user = db.users.find_one({field: user_name, 'done': True})
    if done_user:
        print "  ALREADY DONE! (%s)" % done_user["screen_name"]
        return done_user
    api_args = dict(user)
    metas = api.call('users.show', api_args)
    clean_user_entities(metas)
    if field == "_id":
        print " -> %s" % metas["screen_name"]
    print "  %s friends to get" % metas['friends_count']
    if metas['protected']:
        print "SKIPPING friend for protected account"
    else:
        api_args['count'] = 5000
        api_args['cursor'] = -1
        metas['friends'] = []
        while api_args['cursor']:
            res = api.call('friends.ids', api_args)
            metas['friends'] += res['ids']
            print "  -> query: %s, next: %s" % (len(metas['friends']), res['next_cursor'])
            api_args['cursor'] = res['next_cursor']
    user.update(metas)
    user['done'] = True
    db.users.update({'screen_name': user['screen_name']}, {"$set": user}, upsert=True)
    return user


def build_ego_network(account, db):
    G = nx.DiGraph()
    corpus_ids = db.users.find_one({"screen_name": account})["friends"]
    users = list(db.users.find({"_id": {"$in": corpus_ids}, "protected": False, "lang": {"$ne": "fr"}}))
    for u in users:
        G.add_node(u["id_str"], label=u["screen_name"], friends=u["friends_count"], followers=u["followers_count"], tweets=u["statuses_count"], lang=u["lang"])
    for u in users:
        for f in u.get('friends', []):
            if f in corpus_ids:
                G.add_edge(u["id_str"], str(f))
    return G


if __name__ == "__main__":
    import sys
    from config import MONGO_DATABASE, TWITTER
    api = TwitterWrapper(TWITTER)
    db = MongoClient("localhost", 27017)[MONGO_DATABASE]
    account = sys.argv[1]
    user = collect_user_and_friends(account, api, db)
    for f in user['friends']:
        collect_user_and_friends(f, api, db)
    G = build_ego_network(account, db)
    nx.write_gexf(G, "%s_twitter_egonetwork.gexf" % account)

