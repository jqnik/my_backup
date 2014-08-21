#!/bin/bash

# returns mount return code  

echo "calling 'mount $1 $2'"
mount $1 $2
exit $?
