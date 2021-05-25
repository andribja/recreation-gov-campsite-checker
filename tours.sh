#!/bin/sh
PATH=/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin

for file in tour_params/*
do
    # Source params file
    . $file

    python3 tours.py --start-date $START_DATE --end-date $END_DATE --tours $TOURS --facility $FACILITY > result.txt
    exit_code=$?
    if [ $exit_code == 0 ];
    then
        for email in ${EMAILS[@]}
        do
            echo "RESULTS FOUND - "`date`;
            # Email result
            cat result.txt | /usr/bin/mail -s 'TOURS AVAILABLE' $email;
        done;
    else
        echo "NO RESULTS FOUND - "`date`;
    fi;
done
