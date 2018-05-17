#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json, sys
from datetime import datetime
from pymongo import MongoClient
from config import MONGO_DATABASE

db = MongoClient("localhost", 27017)[MONGO_DATABASE]['users']

headers = ["Nom", u"Prénom", "Compte twitter", u"Élu au", "twitterid", "follows", "id", "name", "screen_name", "created_at", "time_zone", "utc_offset", "protected", "verified", "url", "lang",  "description", "statuses_count", "favourites_count", "followers_count", "following", "friends_count", "listed_count", "geo_enabled", "has_extended_profile", "is_translation_enabled", "is_translator", "contributors_enabled", "default_profile", "default_profile_image", "profile_background_color", "profile_background_image_url", "profile_background_image_url_https", "profile_background_tile", "profile_image_url", "profile_image_url_https", "profile_link_color", "profile_location", "profile_sidebar_border_color", "profile_sidebar_fill_color", "profile_text_color", "profile_use_background_image"]

format_txt = lambda x: '"' + x.replace('"', '""').replace("\n", " ").replace("\r", "") + '"'
format_spe = lambda x: str(x).lower() if x else ""
format_field = lambda x: format_txt(x).encode('utf-8') if type(x) == unicode else format_spe(x)

print (",".join(headers)).encode('utf-8')
for t in db.find(sort=[("_id", 1)]):
    t[u"Élu au"] = u"Conseil de Paris" if t["CR"] == "False" else u"Conseil régional d'IdF" if t["CP"] == "False" else u"Les deux"
    t["twitterid"] = t["screen_name"].lower()
    t["follows"] = "|".join(t["follows"])
    t["created_at"] = datetime.strptime(t['created_at'], '%a %b %d %H:%M:%S +0000 %Y').isoformat().decode("utf8")
    print ",".join([format_field(t.get(a, "")) for a in headers])

