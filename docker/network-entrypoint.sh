#!/bin/sh

if ping -q -c 1 -W 1 host.docker.internal &> /dev/null; then
  printf host.docker.internal
else
  printf "$(netstat -nr | grep '^0\.0\.0\.0' | awk '{print $2}')"
fi
