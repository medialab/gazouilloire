#!/bin/bash

cd "$(dirname "$0")"

pkill -f "python gazouilloire/run.py $(pwd)"
echo "waiting for previous process to terminate..."
elapsed=0
while ps -ef | grep -v "\(grep\|[0-9]  0 [0-9]\)" | grep "python gazouilloire/run.py $(pwd)" > /dev/null && [ $elapsed -lt 300 ]; do
  elapsed=$(($elapsed + 1))
  sleep 1
done
pkill -9 -f "python gazouilloire/run.py $(pwd)"
echo "stopped..."

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
