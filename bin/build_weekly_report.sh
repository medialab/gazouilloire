#!/bin/bash

cd "$(dirname "$0")/.."
source $(which virtualenvwrapper.sh)
deactivate > /dev/null 2>&1
workon gazouilloire

list_filters=$1
if test -z "$list_filters" || ! test -s "$list_filters"; then
  echo "Please input as first argument the path of a file containing a list of filters to report on"
  exit 1
fi

outdir=$2
if test -z "$outdir" || ! test -d "$outdir"; then
  echo "Please input as second argument the path of a directory where to store reports and data"
  exit 1
fi

reporturl=$3

curr_date=$(date +%Y-%m-%d)
curr_time=$(date -d "$cur_date 00:00:00" +%s)
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
  echo "CSV files, medias and report available online at $reporturl/$curr_date

" >> $report
fi

bin/export_csv_as_tcat.py '{"$and": ['"$time_args"']}' > $outdir/all.csv
total=$((`cat $outdir/all.csv | wc -l` - 1))
echo "TOTAL tweets collected this week:
  $total
" >> $report

cat $list_filters | grep . | while read filter; do
  filter_name=$(echo $filter | sed 's/[\\^].//g' | sed 's/|/-/g' | sed 's/[^a-z\-]//gi')
  bin/export_csv_as_tcat.py '{"$and": ['"$time_args"', {"text": re.compile(r"'"$filter"'", re.I)}]}' > $outdir/$filter_name.csv
  total=$((`cat $outdir/$filter_name.csv | wc -l` - 1))
  if [ $total -eq 0 ]; then
    echo "________________________
- FILTER '$filter':
No tweet found for this query this week.
" >> $report
    continue
  fi
  totalrts=$((`csvcut -c "text" $outdir/$filter_name.csv | grep "^RT @\S\+: " | wc -l` - 1))
  csvcut -c "links" $outdir/$filter_name.csv | grep -v '""\|^medias_urls' | tr '|' '\n' | sort | uniq -c | sort -rn > /tmp/$filter_name.links
  nlinks=$((`cat /tmp/$filter_name.links | wc -l`))
  grep "^id,\|https\?://twitter.com/\S\+/photo/[0-9]" $outdir/$filter_name.csv | csvcut -c "medias_urls" | grep -v '""\|^medias_urls' | tr '|' '\n' | sort | uniq -c | sort -rn > /tmp/$filter_name.photos
  nimages=$((`cat /tmp/$filter_name.photos | wc -l`))
  grep "^id,\|https\?://twitter.com/\S\+/video/[0-9]" $outdir/$filter_name.csv | csvcut -c "medias_urls" | grep -v '""\|^medias_urls' | tr '|' '\n' | sort | uniq -c | sort -rn > /tmp/$filter_name.videos
  nvideos=$((`cat /tmp/$filter_name.videos | wc -l`))
  echo "________________________
- FILTER '$filter':
$reporturl/$curr_date/$filter.csv

Total tweets :  $total    including $totalrts RTs
Total different links :  $nlinks
Total different images:  $nimages
Total different videos:  $nvideos

Most RTs:" >> $report
  csvsort -rc "retweet_count" $outdir/$filter_name.csv | csvcut -c "retweet_count,text,id,from_user_name" | grep -v '^retweet_count,\|[0-9]\+,"\?RT @\S\+: ' | sed -r 's/^([0-9]+),/\t\1\t/' | sed -r 's|,([0-9]+),([a-z_]+)$|\t\thttps://twitter.com/\2/statuses/\1|i' | head -3 >> $report
  echo "
Most tweeted links:" >> $report
  head -3 /tmp/$filter_name.links >> $report
  echo "
Most visible images:" >> $report
  head -3 /tmp/$filter_name.photos >> $report
  echo "
Most visible videos:" >> $report
  head -3 /tmp/$filter_name.videos >> $report
  echo "
Sample random tweets:" >> $report
  csvcut -c "text,id,from_user_name" $outdir/$filter_name.csv | grep -v '^id,\|^"\?RT @\S\+: ' | sed -r 's|,([0-9]+),([a-z_]+)$|\t\thttps://twitter.com/\2/statuses/\1|i' | sort -R | head -n 3 >> $report
  echo "
" >> $report
done
