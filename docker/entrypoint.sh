#!/bin/sh

ping -c1 -q host.docker.internal 2>&1 | grep "bad address" >/dev/null \
    && echo "$(netstat -nr | grep '^0\.0\.0\.0' | awk '{print $2}') host.docker.internal" >> /etc/hosts \
    && echo "Hosts File Entry Added for Docker" || :

jet_bridge --media_root=/jet/jet_media --use_default_config=address,config
