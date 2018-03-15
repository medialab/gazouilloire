#!/bin/bash

# Requires to have a "report_filters.txt" file with one line per desired filter report, each being a regexp of the filter, for instance:
# natur
# arb(r|o|ust)
# fl(eur|ori)
# [^d][eéÉ]co
# \\bmurs?\\b
# agr[io]
# for[eêÊ]t
# v[eéÉ]g[eéÉ]t
# trottoir
# pied\\s+d

# Example calls from crontab
# 05 0  2,9,16 10 * bash /store/gazouilloire/gazouilloire-agata/bin/send_reports.sh /store/tweets/agata/ http://gazouilloire.medialab.sciences-po.fr/agata B.O@sciencespo.fr "D.R@sciencespo.fr A.B@gmail.com B.O@sciencespo.fr"
# 01 0    *     * 1 bash /store/gazouilloire/gazouilloire-naturpradi/bin/send_reports.sh /store/tweets/naturpradi/ http://gazouilloire.medialab.sciences-po.fr/naturpradi B.O@sciencespo.fr "D.R@sciencespo.fr A.M@sciencespo.fr G.C@gmail.com A.B@gmail.com B.O@sciencespo.fr"

cd $(dirname $0)/..
OUTDIR=$1
PUBLICURL=$2
CORPUS=$(echo $OUTDIR | sed -r 's|^.*/([^/]+)/?$|\1|')
SENDER=$3
RECEIVERS=$4

bin/build_weekly_report.sh report_filters.txt "$OUTDIR" "$PUBLICURL" 
cat "$OUTDIR"/$(ls -rt "$OUTDIR" | tail -1)/report.txt | mail -s "[$CORPUS] Weekly tweets report" -S replyto="$SENDER" $RECEIVERS 

