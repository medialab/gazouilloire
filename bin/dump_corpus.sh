#!/bin/bash

cd "$(dirname "$0")"/..

db=$(grep '"db":' config.json | awk -F ":" '{print $2}' | sed "s/['\" ]\+//g")
ts=$(date "+%y%m%d-%H%M")

mkdir -p "backups/$ts"
mongodump --db "$db" -o "backups/$ts"

