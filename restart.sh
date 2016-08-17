#!/bin/bash

cd "$(dirname "$0")"
source $(which virtualenvwrapper.sh)
deactivate > /dev/null 2>&1
workon gazouilloire
pkill -f "python gazouilloire/run.py $(pwd)"
echo "waiting for previous process to terminate..."
elapsed=0
while ps -ef | grep -v "\(grep\|[0-9]  0 [0-9]\)" | grep "python gazouilloire/run.py $(pwd)" > /dev/null && [ $elapsed -lt 300 ]; do
  elapsed=$(($elapsed + 1))
  sleep 1
done
pkill -9 -f "python gazouilloire/run.py $(pwd)"
touch runlog.txt
mv -f runlog.txt runlog.txt.old
python gazouilloire/run.py $(pwd) > runlog.txt 2>&1 &
deactivate
if ! [ -z "$1" ]; then
  tail -f runlog.txt
fi
