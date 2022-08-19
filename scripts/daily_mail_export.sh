#!/bin/bash
#
# - Description:
#
# Build and send links by e-mail to daily CSV exports of all last day's tweets from a gazouilloire collection
#
# - Usage:
#
# Place this script in your gazouilloire corpus directory
# Run it by giving as arguments the corpus name, the directory where to place the data exports, the e-mail that will be used to send the message and the e-mails to which it should be sent, and finally the root url of the server where the files will be served, for instance:
#
#   ./daily_mail_export.sh MYCORPUS EXPORTS_DIRECTORY MY@EMAIL.COM "MY@EMAIL.COM MYCOLLEAGUE@EMAIL.COM" "https://MYSERVER.FR/PATH_WHERE_EXPORTS_ARE_SERVED/"
#
# - Prerequisites:
#
# This script supposes gazouilloire was installed within a python environment using PyEnv: https://github.com/pyenv/pyenv-installer
# It also requires that a mail server software such as postfix or exim is installed and properly configured.
# It finally requires that a web server software such as apache2, httpd or nginx is installed and properly configured to serve the desired directory at the desired url.
#
# - Typical cronjob:
#
# The main use of this script is to automate building daily exports and send them by email every day.
# A typical crontab would look something like the following:
#
# m  h dom mon dow   command
# 00 8  *   *   *    bash /data/gazouilloire/daily_mail_export.sh MYCORPUS EXPORTS_DIRECTORY SENDER_EMAIL "RECEIVER_EMAIL_1 RECEIVER_EMAIL_2 ..." "SERVER_URL"


# User arguments to adapt (TODO: transform into CLI args)
CORPUS=$1
OUTDIR=$2
SENDER=$3
RECEIVERS=$4
BASEURL=$5

# Internal variables
CORPUSDIR=$(dirname "$0")
CORPUSENV="gazou-$CORPUS"
OUTFILE="tweets_${CORPUS}_${YESTERDAY}.csv"
YESTERDAY=$(date -d yesterday --iso)
TODAY=$(date --iso)

# Load gazouilloire's python virtualenv
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
export PYENV_VIRTUALENV_DISABLE_PROMPT=1
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"
pyenv activate "$CORPUSENV"

# Load cargo for xsv use
source "$HOME/.cargo/env"

# Export tweets from last day
cd "$CORPUSDIR"
mkdir -p "$OUTDIR"
gazou export --since "$YESTERDAY" --until "$TODAY" --quiet > $OUTDIR/$OUTFILE

# Count tweets and file size
count=$(xsv count $OUTDIR/$OUTFILE)
fsize=$(ls -lh $OUTDIR/$OUTFILE | awk '{print $5}')

# Zip it and measure new size
gzip $OUTDIR/$OUTFILE
zsize=$(ls -lh $OUTDIR/${OUTFILE}.gz | awk '{print $5}')

# Send an e-mail with a link to the gzip and quick metadata
emailtext="
$YESTERDAY

$count tweets
$fsize ($zsize zipped)
$BASEURL/$CORPUS/${OUTFILE}.gz"

echo "$emailtext" | mail -s "[Tweets $CORPUS] Daily export $YESTERDAY" -S replyto="$SENDER" $RECEIVERS

