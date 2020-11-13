#!/bin/bash

cd "$(dirname "$0")/.."
source $(which virtualenvwrapper.sh)
deactivate > /dev/null 2>&1
workon gazouilloire-polarisation

outdir=$1
if test -z "$outdir" || ! test -d "$outdir"; then
  echo "Please input as second argument the path of a directory where to store reports and data"
  exit 1
fi
mkdir -p $outdir

curr_date=$2

if [ -z "$curr_date" ] || [ "$curr_date" = "yesterday" ]; then
  curr_date=$(date -d yesterday +%Y-%m-%d)
fi
curr_time=$(date -d "$curr_date 01:00:00" +%s)
end_time=$(($curr_time + 3600 * 24))
time_args='{"timestamp": {"$gte": '$curr_time'}}, {"timestamp": {"$lt": '$end_time'}}'

dbname=$3
rooturl=$4
sender=$5
receivers=$6

outfile=tweets-${dbname}_$curr_date.csv
python bin/export_csv_as_tcat.py --quiet '{"$and": ['"$time_args"']}' > $outdir/$outfile

lin=$(cat $outdir/$outfile | grep -v '^id' | wc -l)
siz=$(ls -lh $outdir/$outfile | awk '{print $5}')
gzip $outdir/$outfile
zsiz=$(ls -lh $outdir/$outfile.gz | awk '{print $5}')

echo "
$curr_date

$lin tweets
$siz ($zsiz zipped)
$rooturl/$outfile.gz" | mail -s "[Tweets $dbname] Daily export $curr_date" -S replyto="$sender" $receivers


