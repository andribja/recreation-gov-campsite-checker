#!/bin/sh

# Path to git repo
cd ~/recreation-gov-campsite-checker
# Source params file
. ./camping_params

python3 camping.py --start-date $START_DATE --end-date $END_DATE $PARKS > result.txt
RESULTS=`grep -E '^.*[^\n]+.*$' result.txt | wc -l`
if [ $RESULTS -gt "0" ];
then
    echo "RESULTS FOUND - "`date`
    # Email result
    cat result.txt | /usr/bin/mail -s "Campsite" $EMAIL
else
    echo "NO RESULTS FOUND - "`date`;
fi;
