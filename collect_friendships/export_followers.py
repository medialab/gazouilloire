#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json, sys
from datetime import datetime
from pymongo import MongoClient
from config import MONGO_DATABASE

db = MongoClient("localhost", 27017)[MONGO_DATABASE]['users']

headers = [
  "id_str",
  "screen_name",
  "name",
  "description",
  "url",
  "created_at",
  "profile_image_url_https",
  "default_profile",
  "default_profile_image",
  "verified",
  "protected",
  "location",
  "geo_enabled",
  "statuses_count",
  "favourites_count",
  "friends_count",
  "followers_count",
  "listed_count",
  "follows_nofake_science",
  "follows_Rom_GK",
  "follows_Billos_",
  "follows_cuteNukem",
  "follows_Joseph_Garnier",
  "follows_nael_kl",
  "follows_Phanto17",
  "follows_nbonneel",
  "follows_quarkomania",
  "follows_Rasend777",
  "follows_Biorev3",
  "follows_TristanKamin",
  "follows_Evidencebbh",
  "follows_UnMondeRiant",
  "follows_DLDents",
  "follows_buchebuche561",
  "follows_marc_rr",
  "follows_Damkyan_Omega",
  "follows_AnthonyGuihur",
  "follows_LUppsala",
  "follows_AStrochnis",
  "n_followed"
]

format_txt = lambda x: '"' + x.replace('"', '""').replace("\n", " ").replace("\r", "") + '"'
format_field = lambda x: str(int(x)) if type(x) in [int, bool] else format_txt(x).encode('utf-8') if type(x) == unicode else str(x).lower() if x else ""

print (",".join(headers)).encode('utf-8')
for t in db.find(sort=[("_id", 1)]):
    for f in headers:
        if (f.startswith("follows_") or f.endswith("_count")) and (f not in t or not t[f]):
            t[f] = 0
    t["n_followed"] = sum([t[f] for f in headers if f.startswith("follows_")])
    t["created_at"] = datetime.strptime(t['created_at'], '%a %b %d %H:%M:%S +0000 %Y').isoformat().decode("utf8")
    print ",".join([format_field(t.get(a, "")) for a in headers])

