#!/bin/bash

cd "$(dirname "$0")/.."
source $(which virtualenvwrapper.sh)
deactivate > /dev/null 2>&1
workon gazouilloire

list_queries=$1
if test -z "$list_queries" || ! test -s "$list_queries"; then
  echo "Please input as first argument the path of a file containing a list of queries to report on"
  exit 1
fi

list_filters="exclude_filters.txt"
filters=
if [ -s "$list_filters" ]; then
  regfilters="("$(cat exclude_filters.txt | grep . | sed 's/\([[(){}?.+]\)/\\\1/g' | sed 's/]/\\]/g' | tr '\n' '|' | sed 's/|\?$/)/')
  filters=', {"text": {"$not": re.compile(r"'"$regfilters"'", re.I)}}'
fi

outdir=$2
if test -z "$outdir" || ! test -d "$outdir"; then
  echo "Please input as second argument the path of a directory where to store reports and data"
  exit 1
fi

reporturl=$3

curr_date=$4

if [ -z "$curr_date" ]; then
  curr_date=$(date +%Y-%m-%d)
fi
curr_time=$(date -d "$curr_date 00:00:00" +%s)
prev_time=$(($curr_time - 3600 * 24 * 7))
prev_date=$(date -d "@$prev_time" +%Y-%m-%d)
yest_time=$(($curr_time - 1))
yesterday=$(date -d "@$yest_time" +%Y-%m-%d)
time_args='{"timestamp": {"$gte": '$prev_time'}}, {"timestamp": {"$lt": '$curr_time'}}'

outdir=$outdir/$curr_date
mkdir -p $outdir
report=$outdir/report.txt
echo "GAZOUILLOIRE TWEETS REPORT $prev_date 00:00:00 → $yesterday 23:59:59
--------------------------------------------------------------------
" > $report

if ! test -z "$reporturl"; then
  echo "CSV files and report available online at $reporturl/$curr_date
medias at $reporturl/media/

" >> $report
fi

bin/export_csv_as_tcat.py --quiet '{"$and": ['"$time_args""$filters"']}' > $outdir/all.csv
total=$((`cat $outdir/all.csv | wc -l` - 1))
echo "TOTAL tweets collected this week:
  $total
" >> $report

cat $list_queries | grep "\S" | while read query; do
  query_name=$(echo $query | sed 's/[\\^].//g' | sed 's/|/-/g' | sed 's/[^a-z\-]//gi')
  bin/export_csv_as_tcat.py --quiet '{"$and": ['"$time_args""$filters"', {"text": re.compile(r"'"$query"'", re.I)}]}' > $outdir/$query_name.csv
  total=$((`cat $outdir/$query_name.csv | wc -l` - 1))
  if [ $total -eq 0 ]; then
    echo "________________________
- QUERY '$query':
No tweet found for this query this week.
" >> $report
    continue
  fi
  totalrts=$((`csvcut -c "text" $outdir/$query_name.csv | grep "^RT @\S\+: " | wc -l`))
  csvcut -c "links" $outdir/$query_name.csv | grep -v '""\|^medias_urls' | tr '|' '\n' | sort | uniq -c | sort -rn > /tmp/$query_name.links
  nlinks=$((`cat /tmp/$query_name.links | wc -l`))
  grep "^id,\|https\?://twitter.com/\S\+/photo/[0-9]" $outdir/$query_name.csv | csvcut -c "medias_urls" | grep -v '""\|^medias_urls' | tr '|' '\n' | sort | uniq -c | sort -rn > /tmp/$query_name.photos
  nimages=$((`cat /tmp/$query_name.photos | wc -l`))
  grep "^id,\|https\?://twitter.com/\S\+/video/[0-9]" $outdir/$query_name.csv | csvcut -c "medias_urls" | grep -v '""\|^medias_urls' | tr '|' '\n' | sort | uniq -c | sort -rn > /tmp/$query_name.videos
  nvideos=$((`cat /tmp/$query_name.videos | wc -l`))
  echo "________________________
- QUERY '$query':
$reporturl/$curr_date/$query.csv

Total tweets :  $total    including $totalrts RTs
Total different links :  $nlinks
Total different images:  $nimages
Total different videos:  $nvideos

Most RTs:" >> $report
  ct=0
  csvcut -c "text" $outdir/$query_name.csv | grep -v '^text$' | sed 's/^"\?RT @\S\+: //' | sort | uniq -c | sort -gr | head -n 50 | while read line; do
    rts=$((`echo $line | sed 's/ .*$//'` - 1))
    if [ "$rts" -eq 0 ] || [ $ct -ge 3 ]; then break; fi
    text=$(echo $line | sed 's/^[0-9]\+ //' | sed -r 's/(\[|\])/./g')
    if grep ",\"\?$text\"?," $outdir/$query_name.csv > /tmp/retweet.tmp; then
      echo $rts $text $(head -1 /tmp/retweet.tmp | sed -r 's|^([0-9]+),[^,]+,[^,]+,([^,]+),.*$|https://twitter.com/\2/statuses/\1|') >> $report
      ct=$(($ct+1))
    fi
  done
  #csvsort -rc "retweet_count" $outdir/$query_name.csv | csvcut -c "retweet_count,text,id,from_user_name" | grep -v '^retweet_count,\|[0-9]\+,"\?RT @\S\+: ' | sed -r 's/^([0-9]+),/\t\1\t/' | sed -r 's|,([0-9]+),([a-z_]+)$|\t\thttps://twitter.com/\2/statuses/\1|i' | head -3 >> $report
  echo "
Most tweeted links:" >> $report
  head -3 /tmp/$query_name.links >> $report
  echo "
Most visible images:" >> $report
  head -3 /tmp/$query_name.photos >> $report
  echo "
Most visible videos:" >> $report
  head -3 /tmp/$query_name.videos >> $report
  echo "
Sample random tweets:" >> $report
  csvcut -c "text,id,from_user_name" $outdir/$query_name.csv | grep -v '^id,\|^"\?RT @\S\+: ' | sed -r 's|,([0-9]+),([a-z_]+)$|\t\thttps://twitter.com/\2/statuses/\1|i' | sort -R | head -n 3 >> $report
  echo "
" >> $report
done
