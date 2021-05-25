#!/bin/bash
# Run with:
#
# bash get_twitter_oauth2_token.sh $KEY $SECRET > oauth2_token
#
# Then enjoy Twitter's API app functions such as search/tweets or lists/members:
#
# curl -H "$(cat oauth2_token)" "https://api.twitter.com/1.1/search/tweets.json?q=assembleenat+OR+deputes&count=200"
# curl -H "$(cat oauth2_token)" "https://api.twitter.com/1.1/lists/members.json?slug=les-d%C3%A9put%C3%A9s&owner_screen_name=AssembleeNat&skip_status=1"


KEY=$1
SECRET=$2

# Format key/secret following OAuth2 RFC
key=$(python -c "from urllib.parse import urlencode; print(urlencode({'': '$KEY'}).lstrip('='))")
secret=$(python -c "import sys; from urllib.parse import urlencode; print(urlencode({'': '$SECRET'}).lstrip('='))")

# Get token by forging exact request
# token=$(echo -n "$key:$secret" | base64 -w 100)
# curl -s -X POST -A "twitter search app" -H "Authorization: Basic $token" -H "Content-Type: application/x-www-form-urlencoded;charset=UTF-8" -d "grant_type=client_credentials" "https://api.twitter.com/oauth2/token" > /tmp/twitter-token

# Or more simply thanks to curl's integrated secure user auth 
curl -s -u "$key:$secret" -d "grant_type=client_credentials" "https://api.twitter.com/oauth2/token" > /tmp/twitter-token

# Extract token from json and print it out
if cat /tmp/twitter-token | grep '"token_type":"bearer"' | grep '"access_token":"' > /dev/null; then
  cat /tmp/twitter-token | sed 's/^.*"access_token":"\([^"]\+\)".*$/\1\n/'
else
  print "Could not get bearer token, please check your key/secret" >&2
fi

