#!/bin/bash

ogrinfo -al $1 | grep Extent | tr -d '()' | awk -F'[ ,]+' '{print $2 " " $3 " " $5" " $6}'

