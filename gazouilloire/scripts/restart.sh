#!/bin/bash
#
# - Description:
#
# Restart safely automatically a gazouilloire collection
#
# - Usage:
#
# Place this script in your gazouilloire corpus directory
# Run it by giving it the corpus name as argument, for instance:
#
#   ./restart.sh MYCORPUS
#
# It will automatically try to use pyenv to activate a virtualenv named 'gazou-MYCORPUS' but you can force another env name like this:
#
#   ./restart.sh MYCORPUS MYENV
#
# If a third argument is given as an integer, ElasticSearch will be tested before restarting gazouilloire. If ES is down, the script will try to restart it for this number of seconds. For instance:
#
#   ./restart.sh MYCORPUS MYENV 60
#
# The user running this script must be granted sudo rights with no password for the specific ES restart command so that this option can work properly.
# You can do this for instance by adding a file to /etc/sudoers.d/:
#
#   sudo visudo -f /etc/sudoers.d/gazouilloire 
# Then add within it a line similar to the following:
#
#   username ALL=(ALL) NOPASSWD: /usr/sbin/service elasticsearch restart
#
# - Prerequisites:
#
# This script supposes gazouilloire was installed within a python environment using PyEnv: https://github.com/pyenv/pyenv-installer
#
# - Typical cronjobs:
#
# The main use of this script is to automate restarts at server reboot and every day in case of unexpected crashes.
# ES autorestarts at reboot should not be enabled if multiple gazouilloire are set on the same machine, otherwise it might try to restart it in parallel multiple times which sounds like a bad idea.
# So a typical crontab would look something like the following:
#
# m  h dom mon dow   command
# @reboot            bash /data/gazouilloire/restart.sh CORPUSNAME CORPUSENV
# 00 4  *   *   *    bash /data/gazouilloire/restart.sh CORPUSNAME CORPUSENV TIMEOUT_ES


# Corpus name as argument 
CORPUS=$1

# Corpus python environment assumed to be named gazou-CORPUSNAME if not input
CORPUSENV=$2
if [ -z "$2" ]; then
  CORPUSENV="gazou-$CORPUS"
fi

TIMEOUT=0
if [ ! -z "$3" ]; then
  TIMEOUT=$3
fi

# Corpus directory assumed to be the same as the script's
CORPUSDIR=$(dirname "$0")
cd $CORPUSDIR

# Setup and activate Python environment using PyEnv
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
export PYENV_VIRTUALENV_DISABLE_PROMPT=1
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"
pyenv activate "$CORPUSENV"

# Check collection's status to ensure ElasticSearch is running and reboot it when possible
NOW=$(date +"%s")
WAIT_UNTIL=$(($NOW + $TIMEOUT))
while [ "$NOW" -lt "$WAIT_UNTIL" ] && gazou status "$CORPUSDIR" 2>&1 | grep "Connection to Elasticsearch failed."; do
  echo "ElasticSearch seems to be down, trying to restart it..."
  sudo service elasticsearch restart
  sleep 2
  NOW=$(date +"%s")
done

# Restart the corpus after waiting 5 minutes for the previous process to shut down cleanly
gazou restart "$CORPUSDIR" --timeout 300

# Display quick stats on the corpus as of now
gazou status "$CORPUSDIR"

# Warn explicitly if tweets data in ES reached more than 100Go
if gazou status -l "$CORPUSDIR" 2>&1 | grep "name: " -A 2 | grep "disk space tweets: [0-9]\{3,\}[0-9\.]*GB" > /dev/null; then
  echo
  echo
  echo "!!! WARNING !!!"
  echo "---------------"
  echo "Tweets data of an ElasticSearch index consumes more than 100Go, you should maybe restart your corpus on a fresh new index:"
  gazou status -l "$CORPUSDIR" 2>&1 | grep -B 2 "disk space tweets: [0-9]\{3,\}[0-9\.]*GB"
fi

