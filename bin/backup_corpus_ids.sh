#!/bin/bash

cd $(dirname $0)/..

if ! test -z "$1"; then
  BACKUPDIR=$1
else
  BACKUPDIR=.
fi

if ! test -z "$2"; then
  DBNAME=$2
else
  DBNAME=$(grep '"db":' config.json | awk -F '"' '{print $4}')
fi

if mongo --version | grep -q 'version: 2'; then
  CSVOPT="--csv"
else
  CSVOPT="--type=csv"
fi

mongoexport -d "$DBNAME" -c tweets -f _id $CSVOPT --quiet > "$BACKUPDIR/${DBNAME}_tweets_ids.csv"
if [ "$?" -eq 0 ] && test -s "$BACKUPDIR/${DBNAME}_tweets_ids.csv"; then
  gzip -q -f "$BACKUPDIR/${DBNAME}_tweets_ids.csv"
else
  echo "WARNING, it seems there was an error while backupping tweets IDs in $BACKUPDIR/${DBNAME}_tweets_ids.csv"
fi
