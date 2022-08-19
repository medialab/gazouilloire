#!/bin/bash
#
# - Description:
#
# Easily import or export gazouilloire's ElasticSearch indices as dumps
#
# - Usage:
#
# Place this script in your gazouilloire corpus directory
# Export a dump of current ElasticSearch tweets and links index (including all different monthly indices when using multi_index mode) into a specific Export directory:
#
#   ./elasticdump.sh export EXPORTDIR
#
# Reimport a previously exported dump from a directory IMPORTDIR at the IMPORTDATE into new ElasticSearch indices named NEW_INDEX_BASENAME:
#
#   ./elasticdump.sh import IMPORTDIR IMPORTDATE NEW_INDEX_BASENAME
#
# - Prerequisites:
#
# This script supposes the Javascript tool "elasticdump" was installed using npm, which requires NodeJS: https://nodejs.dev/
#
#   npm install -g elasticdump


# Corpus directory assumed to be the same as the script's
CORPUSDIR=$(dirname "$0")
cd $CORPUSDIR

ACTION=$1

if [ "$ACTION" != "import" ] && [ "$ACTION" != "export" ]; then
  echo "The first argument must be either import or export."
  exit
fi

# Exports directory assumed to be the same by default
EXPORTDIR=$2
if ! test -z "$EXPORTDIR"; then
  EXPORTDIR="$EXPORTDIR/"
fi

DBNAME=$(grep '"db_name":' config.json | awk -F '"' '{print $4}')
DBHOST=$(grep '"host":' config.json | awk -F '"' '{print $4}')
DBPORT=$(grep '"port":' config.json | awk -F '"' '{print $4}')

MULTI=$(grep '"multi_index":' config.json | awk -F '"' '{print $4}')

DAT=$(date +%Y%m%d)

# Run exports
if [ "$ACTION" = "export" ]; then

# Export a gzipped dump of your gazouilloire links index
  elasticdump --fsCompress --input http://$DBHOST:$DBPORT/${DBNAME}_links --output ${EXPORTDIR}${DAT}_${DBNAME}-links_elasticdump.json.gz

# Export a gzipped dump of your gazouilloire tweets index
  if [ "$MULTI" = "false" ]; then
    elasticdump --fsCompress --input http://$DBHOST:$DBPORT/${DBNAME}_tweets --output ${EXPORTDIR}${DAT}_${DBNAME}-tweets_elasticdump.json.gz
  else
# If multi_index is set to true in config.json, there are multiple indexes to backup which you can list using: gazou status -l
# Let's back them all up:
    gazou status -l | grep "^name:" | awk '{print $2}' | while read IDX; do
      elasticdump --fsCompress --input http://$DBHOST:$DBPORT/$idx --output ${EXPORTDIR}${DAT}_${IDX}_elasticdump.json.gz
    done
  fi

  exit

fi

# Run imports

IMPORTDAT=$3
IMPORTDB=$4

# Reimport a previously exported dump of links into a new index
elasticdump --fsCompress --input ${EXPORTDIR}${IMPORTDAT}_*-links_elasticdump.json.gz --output http://$DBHOST:$DBPORT/${IMPORTDB}_links

# Reimport a previously exported dump of tweets into a new index
if [ "$MULTI" = "false" ]; then
  elasticdump --fsCompress --input ${EXPORTDIR}${IMPORTDAT}_*-tweets_elasticdump.json.gz --output http://$DBHOST:$DBPORT/${IMPORTDB}_tweets
else
# If multi_index is set to true in config.json, there were multiple indexes backed up which you can list using: ls -l EXPORTDIR/IMPORTDAT_*_elasticdump.json.gz
# Let's reload them all:
  cd $EXPORTDIR
  ls ${IMPORTDAT}_*_elasticdump.json.gz |
   grep -v "-links_elasticdump.json.gz" |
   while read DUMPFILE; do
    IDX=$(echo $DUMPFILE | sed 's/'${IMPORTDAT}'_//' | sed 's/_elasticdump.json.gz//')
    elasticdump --fsCompress --input $DUMPFILE --output http://$DBHOST:$DBPORT/$IDX
   done
fi

