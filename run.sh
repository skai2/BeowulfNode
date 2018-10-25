#!/bin/bash

NUMBER=1
if [ "$1" != "" ]; then
  NUMBER=$1
  echo $NUMBER
fi

for ((i=1; i<=$NUMBER; i++))
do
    x-terminal-emulator -e "python3 pi_monte_carlo_distributed.py"&
done
