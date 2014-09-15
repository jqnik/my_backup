#!/bin/sh
echo "commandline: rsync $1"
rsync $1
exit $? 
