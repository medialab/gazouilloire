#!/bin/bash

# - Usage:
# Place this script in your gazouilloire corpus directory
# Run it by giving it the corpus name as argument, for instance:
# ./restart.sh mycorpus
#
# - Prerequisites:
# This script supposes gazouilloire was installed within a python environment using PyEnv:
# https://github.com/pyenv/pyenv-installer
#
# - Typical cronjobs:
# The main use of this script is to automate restarts at server reboot
# and every day in case of unexpected crashes.
# So a typical crontab would look something like the following:
#
# m  h dom mon dow   command
# @reboot            bash /data/gazouilloire/restart.sh CORPUSNAME
# 00 4  *   *   *    bash /data/gazouilloire/restart.sh CORPUSNAME


# Corpus name as argument 
CORPUS=$1

# Corpus directory assumed to be the same as the script's
CORPUSDIR=$(dirname "$0")
cd $CORPUSDIR

# Corpus python environment assumed to be named gazou-CORPUSNAME
CORPUSENV="gazou-$CORPUS"

# Setup and activate Python environment using PyEnv
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
export PYENV_VIRTUALENV_DISABLE_PROMPT=1
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"
pyenv activate "$CORPUSENV"

# Restart the corpus after waiting 5 minutes for the previous process to shut down cleanly
gazou restart "$CORPUSDIR" --timeout 300

# Display quick stats on the corpus as of now
gazou status "$CORPUSDIR"

