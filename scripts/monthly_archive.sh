#!/bin/bash
#
# - Description:
#
# [multi_index] Build monthly archive exports of inactive indices to close or delete them
#
# - Usage:
#
# Place this script in your gazouilloire corpus directory
# Run it by giving it the corpus virtualenv as argument, for instance:
#
#   ./monthly_export.sh MYENV
#
# Set the second parameter to "close" or "delete" if you want to close or delete old indices after exporting their content, like this:
#
#   ./monthly_export.sh MYENV delete
#
# - Prerequisites:
#
# This script supposes gazouilloire was installed within a python environment using PyEnv: https://github.com/pyenv/pyenv-installer
#
# - Typical cronjobs:
#
# The main use of this script is to automate archives every month.
# So a typical crontab would look something like the following:
#
# m  h dom mon dow   command
# 00 4  1   *   *    bash /data/gazouilloire/monthly_export.sh MYENV delete


TODAY=$(date --iso)

# Corpus directory assumed to be the same as the script's
CORPUSDIR=$(dirname "$0")
cd $CORPUSDIR

# Corpus python environment
CORPUSENV=$1

# Old indices will stay open if no input.
CLOSE=$2


# Setup and activate Python environment using PyEnv
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
export PYENV_VIRTUALENV_DISABLE_PROMPT=1
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"
pyenv activate "$CORPUSENV"

# Export inactive indices (older than the value of nb_past_months set in config.json)
gazou count --index inactive --step days > "collected_tweets_per_day_${TODAY}.csv"
gazou export --index inactive --step hours > "monthly_export_${TODAY}.csv"

# Compress the monthly export
gzip "monthly_export_${TODAY}.csv"

if [ "$?" = 0 ]; then
  # Close or delete inactive indices
  if [[ $CLOSE == "close" ]]; then
    gazou close --index inactive
  elif [[ $CLOSE == "delete" ]]; then
    gazou close --index inactive --delete
  fi
fi
