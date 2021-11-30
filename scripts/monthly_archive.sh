#!/bin/bash

# - Usage:
# Place this script in your gazouilloire corpus directory
# Run it by giving it the corpus name as argument, for instance:
# ./monthly_export.sh mycorpus
#
# It will automatically try to use pyenv to activate a virtualenv
# named 'gazou-mycorpus' but you can force another env name like this:
#   ./monthly_export.sh mycorpus myenv
#
# Set the third parameter to "close" or "delete"
# if you want to close or delete old indices after exporting their content, like this:
#   ./monthly_export.sh mycorpus myenv delete
#
# - Prerequisites:
# This script supposes gazouilloire was installed within a python environment using PyEnv:
# https://github.com/pyenv/pyenv-installer
#
# - Typical cronjobs:
# The main use of this script is to automate export every month
# So a typical crontab would look something like the following:
#
# m  h dom mon dow   command
# 00 4  1   *   *    bash /data/gazouilloire/monthly_export.sh CORPUSENV delete

TODAY=$(date --iso)

# Corpus directory assumed to be the same as the script's
CORPUSDIR=$(dirname "$0")
cd $CORPUSDIR

# Corpus python environment assumed to be named gazou-CORPUSNAME if not input
CORPUSENV=$1

# Old indices will stay open if no input.
CLOSE=$2
if [ -z "$2" ]; then
  CLOSE=""
fi


# Setup and activate Python environment using PyEnv
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
export PYENV_VIRTUALENV_DISABLE_PROMPT=1
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"
pyenv activate "$CORPUSENV"

# Export inactive indices (older than the value of nb_past_months set in config.json)
gazou export --index inactive > "monthly_export_${TODAY}.csv"

# Close or delete inactive indices
if [[ $CLOSE == "close" ]]; then
  gazou close --index inactive
elif [[ $CLOSE == "delete" ]]; then
  gazou close --index inactive --delete
fi

