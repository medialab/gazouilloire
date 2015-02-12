#!/bin/bash

cd "$(dirname "$0")"/..

db=$(grep '"db":' config.json | awk -F ":" '{print $2}' | sed "s/['\" ]\+//g")
ts=$1
if [ -z "$ts" ]; then
  ts=$(ls "backups" | tail -n 1)
fi

mongorestore --db "$db" "backups/$ts/$db/"
