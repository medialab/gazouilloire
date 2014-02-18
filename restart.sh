#!/bin/bash

pkill -f "python gazouilloire/run.py"
sleep 1
touch runlog.txt
mv -f runlog.txt runlog.txt.old
python gazouilloire/run.py > runlog.txt 2>&1 &
tail -f runlog.txt

