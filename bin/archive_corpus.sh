#!/bin/bash

ARCHIVES=$1

NOW=$(date +%y%m%d)
DB=$(grep '"db":' config.json | awk -F '"' '{print $4}')
FILENAME="${NOW}_${DB}"

echo "autoedit config file to add dates & total tweets..."
STARTTS=$(mongo --quiet $DB --eval "db.tweets.find().sort({collected_at_timestamp: 1}).limit(1)[0].collected_at_timestamp")
STARTDATE=$(date +'%Y-%m-%d %H:%M:%S' -d @$STARTTS)
ENDTS=$(mongo --quiet $DB --eval "db.tweets.find().sort({timestamp: -1}).limit(1)[0].timestamp")
ENDDATE=$(date +'%Y-%m-%d %H:%M:%S' -d @$ENDTS)
TOTALLINKS=$(mongo --quiet $DB --eval "db.links.count()")
TOTALTWEETS=$(mongo --quiet $DB --eval "db.tweets.count()")
sed -ri 's/^(.*"language.*",)$/    "start_real": "'"$STARTDATE"'",\n    "end": "'"$ENDDATE"'",\n    "total_tweets": '"$TOTALTWEETS"',\n    "total_links": '"$TOTALLINKS"',\n\1/' config.json
echo "DATES: $STARTDATE -> $ENDDATE"
echo "TWEETS: $TOTALTWEETS"
echo "LINKs: $TOTALLINKS"
echo

echo "backup config, search_state and logs to $ARCHIVES..."
cp config.json $ARCHIVES/
mv .search_state.json $ARCHIVES/
gzip logs/*.log
mv logs $ARCHIVES/
echo

source $(which virtualenvwrapper.sh)
deactivate > /dev/null 2>&1
$(grep workon restart.sh)

echo "resolve leftover urls..."
bin/complete_links_resolving.py
echo

echo "backup corpus ids to /archives/twitter/backups..."
bin/backup_corpus_ids.sh /archives/twitter/backups
echo

echo "backup all links to $ARCHIVES/${FILENAME}_resolved-urls.csv.gz..."
bin/export_resolved_links.py | gzip > $ARCHIVES/${FILENAME}_resolved-urls.csv.gz
echo

echo "backup all tweets to $ARCHIVES/${FILENAME}_full.csv.gz..."
bin/export_csv_as_tcat.py | gzip > $ARCHIVES/${FILENAME}_full.csv.gz
echo

echo "Check residual files then delete DB"
git status
ls -larth . $ARCHIVES

