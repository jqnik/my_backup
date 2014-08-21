#!/bin/bash

# returns 0 if device path is mounted, 1 otherwise  

found=`mount|egrep $1| wc -l`

if [[ $found -gt 0 ]]
	then exit 0
fi
exit 1
