#!/bin/bash

cd "$(dirname "$0")"

DELAY=$1
if [ -z "$DELAY" ]; then
  DELAY=300
fi

pkill -f "python gazouilloire/run.py $(pwd)"
echo "waiting ${DELAY}s for previous process to terminate..."
elapsed=0
while ps -ef | grep -v "\(grep\|[0-9]  0 [0-9]\)" | grep "python gazouilloire/run.py $(pwd)" > /dev/null && [ $elapsed -lt $DELAY ]; do
  elapsed=$(($elapsed + 1))
  sleep 1
done
pkill -9 -f "python gazouilloire/run.py $(pwd)"
echo "stopped..."
