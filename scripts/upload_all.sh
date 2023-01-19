#!/bin/sh
cd "$(dirname "$0")"

../packages/jet_bridge_base/upload.sh
../packages/jet_bridge/upload.sh
../packages/jet_django/upload.sh
