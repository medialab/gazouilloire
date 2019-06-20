#!/bin/bash

cd "$(dirname "$0")"

./stop.sh

echo "zipping old logs..."
mkdir -p logs
gzip logs/*.log
LOG="logs/$(date +%Y%m%d-%H%M).log"

echo "restarting..."
source $(which virtualenvwrapper.sh)
deactivate > /dev/null 2>&1
workon gazouilloire
python gazouilloire/run.py $(pwd) > $LOG 2>&1 &
deactivate

if [ -z "$1" ]; then
  tail -f $LOG
fi
