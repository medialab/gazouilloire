#!/bin/bash
#
# - Description:
#
# Export a simple CSV of only the ids of all tweets from a gazouilloire collection
#
# - Usage:
#
# Place this script in your gazouilloire corpus directory
# Run it directly and get the backup in the current directory:
#
#   ./backup_corpus_ids.sh
#
# Or give it an optional path where to store the backup:
#
#   ./backup_corpus_ids.sh /backups/tweets/MYCORPUS/
#
# It will automatically try to use pyenv to activate a virtualenv given in .python-version or named 'gazou-CORPUSDBNAME' otherwise, but you can also force another env as a 2nd argument like this:
#
#   ./backup_corpus_ids.sh /backups/tweets/MYCORPUS/ MYENV
#
# - Prerequisites:
#
# This script supposes gazouilloire was installed within a python environment using PyEnv: https://github.com/pyenv/pyenv-installer
#
# - Typical cronjob:
#
# The main use of this script is to automate a daily backup of all collected tweets' ids for a corpus.
# A typical crontab would look something like the following:
#
# m  h dom mon dow   command
# 00 2  *   *   *    bash /data/gazouilloire/backup_corpus_ids.sh BACKUPS_DIR


# Corpus directory assumed to be the same as the script's
CORPUSDIR=$(dirname "$0")
cd $CORPUSDIR

DBNAME=$(grep '"db_name":' config.json | awk -F '"' '{print $4}')

# Backup directory assumed to be the same by default
BACKUPDIR=$1
if ! test -z "$BACKUPDIR"; then
  BACKUPDIR="$BACKUPDIR/"
fi

# Corpus python environment assumed to be named gazou-CORPUSNAME if not input
if ! test -z "$2"; then
  CORPUSENV=$2
elif test -s ".python-version"; then
  CORPUSENV=$(cat .python-version)
else
  CORPUSENV=gazou-$DBNAME
fi

# Setup and activate Python environment using PyEnv
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
export PYENV_VIRTUALENV_DISABLE_PROMPT=1
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"
pyenv activate "$CORPUSENV"

# Export corpus ids
if grep '"multi_index"' config.json | grep 'true' > /deb/null; then
  gazou status -l | grep '^name:' | sed -r 's/^.*_tweets_([0-9]{4}_[0-9]{2})$/\1/' | while read month; do
    gazou export -s id --sort no -i $month > ${BACKUPDIR}${DBNAME}_tweets_ids_$month.csv
    gzip -f ${BACKUPDIR}${DBNAME}_tweets_ids_$month.csv
  done
else
  gazou export -s id --sort no > ${BACKUPDIR}${DBNAME}_tweets_ids.csv
  gzip -f ${BACKUPDIR}${DBNAME}_tweets_ids.csv
fi

