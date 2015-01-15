#!/bin/bash

cd "$(dirname "$0")"
source $(which virtualenvwrapper.sh)
deactivate > /dev/null 2>&1
workon gazouilloire
if test -s gazouilloire.pid && ps -ef | grep "$(cat gazouilloire.pid)" | grep "python gazouilloire/run.py"; then
  kill -9 "$(cat gazouilloire.pid)"
  sleep 1
fi
touch runlog.txt
mv -f runlog.txt runlog.txt.old
python gazouilloire/run.py > runlog.txt 2>&1 &
echo $! > gazouilloire.pid
deactivate
tail -f runlog.txt
