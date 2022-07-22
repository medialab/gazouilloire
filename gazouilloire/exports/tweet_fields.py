TWEET_FIELDS = [
    'id',                             # digital ID
    'timestamp_utc',                  # UNIX timestamp of creation - UTC time
    'local_time',                     # ISO datetime of creation - local time
    'user_screen_name',               # author's user text ID (@user) (at collection time)
    'text',                           # message's text content
    # 'filter_level',                   # maximum value of the filter_level parameter which may be used and still stream this Tweet
    'possibly_sensitive',             # whether a link present in the message might contain sensitive content according to Twitter
    # 'withheld_copyright',             # whether the tweet might be censored by Twitter following copyright requests, ignorable
    # 'withheld_scope',                 # whether the content withheld is the 'status' or a 'user', ignorable
    # 'withheld_countries',             # list of ISO country codes in which the message is withheld, separated by |, ignorable
    # 'truncated',                      # whether the tweet is bigger than 140 characters, obsolete
    'retweet_count',                  # number of retweets of the message (at collection time)
    'like_count',                     # number of likes of the message (at collection time)
    'reply_count',                    # number of answers to the message, dropped by Twitter (since Oct 17, now charged), unreliable and ignorable
    'lang',                           # language of the message automatically identified by Twitter's algorithms (equals 'und' when no language could be detected)
    'to_username',                    # text ID of the user the message is answering to
    'to_userid',                      # digital ID of the user the message is answering to
    'to_tweetid',                     # digital ID of the tweet the message is answering to
    # 'source',                         # medium used by the user to post the message, now exported in source_name and source_url fields
    'source_name',                    # name of the medium used to post the message
    'source_url',                     # link to the medium used to post the message
    'user_location',                  # location declared in the user's profile (at collection time)
    'lat',                            # latitude of messages geolocalized
    'lng',                            # longitude of messages geolocalized
    'user_id',                        # author's user digital ID
    'user_name',                      # author's detailed textual name (at collection time)
    'user_verified',                  # whether the author's account is certified
    'user_description',               # description given in the author's profile (at collection time)
    'user_url',                       # link to a website given in the author's profile (at collection time)
    'user_image',                     # link to the image avatar of the author's profile (at collection time)
    # 'user_utcoffset',                 # time offset due to the user's timezone, dropped by Twitter (since May 18), ignorable
    # 'user_timezone',                  # timezone declared in the user's profile, dropped by Twitter (since May 18), ignorable
    # 'user_lang',                      # language declared in the user's profile (at collection time), dropped by Twitter (since May 19), ignorable
    'user_tweets',                    # number of tweets sent by the user (at collection time)
    'user_followers',                 # number of users following the author (at collection time)
    'user_friends',                   # number of users the author is following (at collection time)
    'user_likes',                     # number of likes the author has expressed (at collection time)
    'user_lists',                    # number of users lists the author has been included in (at collection time)
    'user_created_at',                # ISO datetime of creation of the author's account
    'user_timestamp_utc',             # UNIX timestamp of creation of the author's account - UTC time
    'collected_via',                  # How we received the message: 'stream', 'search', 'retweet' (the original tweet was
                                    # contained in the retweet metadata), 'quote' (the original tweet was contained in
                                    # the quote metadata), 'thread' (the tweet is part of the same conversation as a
                                    # tweet collected via search or stream). If the message was collected via multiple
                                    # ways, they are separated by |
    'match_query',                    # whether the tweet was retrieved because it matches the query, or whether it was
                                    # collected via 'quote' or 'thread'
    'retweeted_id',                   # digital ID of the retweeted message
    'retweeted_user',                 # text ID of the user who authored the retweeted message
    'retweeted_user_id',              # digital ID of the user who authoring the retweeted message
    'retweeted_timestamp_utc',        # UNIX timestamp of creation of the retweeted message - UTC time
    'quoted_id',                      # digital ID of the retweeted message
    'quoted_user',                    # text ID of the user who authored the quoted message
    'quoted_user_id',                 # digital ID of the user who authoring the quoted message
    'quoted_timestamp_utc',           # UNIX timestamp of creation of the quoted message - UTC time
    'collection_time',                # ISO datetime of message collection - local time
    'url',                            # url of the tweet (to get a view of the message directly on Twitter)
    'place_country_code',             # if the tweet has an associated 'place', country code of that place
    'place_name',                     # if the tweet has an associated 'place', name of that place
    'place_type',                     # if the tweet has an associated 'place', type of that place ('city', 'admin', etc.)
    'place_coordinates',              # if the tweet has an associated 'place', coordinates of that place, separated by |
    'links',                          # list of links included in the text content, with redirections resolved, separated by |
    'domains',                        # list of domain names in the links fields, separated by |
    'media_urls',                     # list of links to images/videos embedded, separated by |
    'media_files',                    # list of filenames of images/videos embedded and downloaded, separated by |, ignorable when medias collections isn't enabled
    'media_types',                    # list of media types (photo, video, animated gif), separated by |
    'mentioned_names',                # list of text IDs of users mentionned, separated by |
    'mentioned_ids',                  # list of digital IDs of users mentionned, separated by |
    'hashtags'                        # list of hashtags used, lowercased, separated by |
]


TWEET_FIELDS_TCAT = {

    'identical_fields': {
        'id': 'id',
        'timestamp_utc': 'time',
        'local_time': 'created_at',
        'user_screen_name': 'from_user_name',
        'text': 'text',
        'possibly_sensitive': 'possibly_sensitive',
        'retweet_count': 'retweet_count',
        'like_count': 'favorite_count',
        'lang': 'lang',
        'to_username': 'to_user_name',
        'to_userid': 'to_user_id',
        'to_tweetid': 'in_reply_to_status_id',
        'quoted_id': 'quoted_status_id',
        'user_location': 'location',
        'lat': 'lat',
        'lng': 'lng',
        'user_id': 'from_user_id',
        'user_name': 'from_user_realname',
        'user_verified': 'from_user_verified',
        'user_description': 'from_user_description',
        'user_url': 'from_user_url',
        'user_image': 'from_user_profile_image_url',
        'user_tweets': 'from_user_tweetcount',
        'user_followers': 'from_user_followercount',
        'user_friends': 'from_user_friendcount',
        'user_likes': 'from_user_favourites_count',
        'user_lists': 'from_user_listed',
        'user_created_at': 'from_user_created_at',
        'links': 'urls_expanded',
        'domains': 'domains',
        'mentioned_ids': 'mentions',
        'hashtags': 'hashtags',
        'media_urls': 'media_urls',
        'media_types': 'media_type'
    },

    'modified_fields': [
        'source'
    ],

    'removed_fields': [
        'filter_level',
        'witheld_copyright',
        'withheld_scope',
        'truncated',
        'from_user_utcoffset',
        'from_user_timezone',
        'from_user_lang',
        'from_user_withheld_scope',
        'urls',
        'media_id',
        'media_indice_start',
        'media_indice_end',
        'photo_sizes_width',
        'photo_sizes_height',
        'photo_resize',
    ],

    'added_fields': [
        'user_timestamp_utc',
        'source_url',
        'source_name',
        'collected_via',
        'match_query',
        'retweeted_id',
        'retweeted_user',
        'retweeted_user_id',
        'retweeted_timestamp_utc',
        'quoted_user',
        'quoted_user_id',
        'quoted_timestamp_utc',
        'collection_time',
        'url',
        'place_country_code',
        'place_name',
        'place_type',
        'place_coordinates',
        'media_files',
        'mentioned_names'
    ],
}