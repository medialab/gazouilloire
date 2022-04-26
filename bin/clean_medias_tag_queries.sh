cd media
find . -name "*\?*" | while read f; do fout=$(echo $f | sed 's/?tag=.*//'); echo "$f => $fout"; mv $f $fout; done
