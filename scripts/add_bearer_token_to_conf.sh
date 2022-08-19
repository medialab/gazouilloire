#!/bin/bash
#
# - Description:
#
# Complete config.json with Twitter API's bearer token for rare cases it requires it
#
# - Usage:
#
#   ./add_twitter_bearer_token_to_conf.sh PATH_TO_CONFIG/config.json
#
# or from the directory in which your config.json file relies:
#
#   ./add_twitter_bearer_token_to_conf.sh


CONFIG_FILE="config.json"
if ! test -z "$1"; then
  CONFIG_FILE=$1
fi

if ! test -s "$CONFIG_FILE"; then
  echo "ERROR: can not find $CONFIG_FILE" >&2
  exit
fi

KEY=$(grep '"key":' $CONFIG_FILE | awk -F '"' '{print $4}')
SECRET=$(grep '"secret":' $CONFIG_FILE | awk -F '"' '{print $4}')

curl -s -u "$KEY:$SECRET" -d "grant_type=client_credentials" "https://api.twitter.com/oauth2/token" > /tmp/twitter-token

if cat /tmp/twitter-token | grep '"token_type":"bearer"' | grep '"access_token":"' > /dev/null; then
  TOKEN=$(cat /tmp/twitter-token | sed 's/^.*"access_token":"\([^"]\+\)".*$/\1/')
  sed -i 's/\("twitter":\s*{\)/\1\n        "bearer_token": "'"$TOKEN"'",/' $CONFIG_FILE &&
  echo "OK: $CONFIG_FILE was updated with bearer_token $TOKEN" ||
  echo "ERROR: could not edit $CONFIG_FILE" >&2
else
  print "ERROR: Could not get bearer token, please check your key/secret" >&2
fi

