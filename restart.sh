#!/bin/bash

cd "$(dirname "$0")"
source $(which virtualenvwrapper.sh)
deactivate > /dev/null 2>&1
workon gazouilloire
pkill -9 -f "python gazouilloire/run.py $(pwd)"
sleep 1
touch runlog.txt
mv -f runlog.txt runlog.txt.old
python gazouilloire/run.py $(pwd) > runlog.txt 2>&1 &
deactivate
tail -f runlog.txt
