#!/bin/bash

cd $(dirname $0)/..
DB=$(grep '"db":' config.json | sed -r 's/^.*":\s*"([^"]*)".*$/\1/')
mongoexport --jsonArray -d "$DB" -c tweets -o "$DB".json > /dev/null 2>&1
