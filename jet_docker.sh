#!/bin/sh
set -e

# Jet Bridge
# https://github.com/jet-admin/jet-bridge
#
# This script is meant for quick & easy install via:
#
#   sh <(curl -s https://raw.githubusercontent.com/jet-admin/jet-bridge/master/jet_docker.sh)"


# Check if docker is installed
if ! [ -x "$(command -v docker)" ]; then
    echo
	echo "ERROR:"
	echo "    Docker is not found on your system"
	echo "    Install Docker by running the following command:"
	echo
	echo "        sh <(curl -s https://get.docker.com)"
	echo
	echo "    or follow official documentation"
	echo
	echo "        https://docs.docker.com/install/"
	echo
	exit 1
fi

# Check if docker is running
docker_state=$(docker info >/dev/null 2>&1)
if [[ $? -ne 0 ]]; then
    echo
    echo "ERROR:"
    echo "    Docker does not seem to be running, run it first and retry"
    echo
    exit 1
fi

CONFIG_FILE="${PWD}/jet.conf"

# Checking if config file exists
if [ -f "$CONFIG_FILE" ]; then
    echo
	echo "    There is an existing config file will be used:"
	echo "    ${CONFIG_FILE}"
	echo "    You can edit it to change settings"
	echo
else
    docker rm --force jet_bridge &> /dev/null
    docker run \
        -p 8888:8888 \
        --name=jet_bridge \
        -it \
        -v $(pwd):/jet \
        -e DATABASE_HOST=host.docker.internal \
        -e ARGS=config \
        jetadmin/jetbridge
fi

PORT=$(awk -F "=" '/^PORT=/ {print $2}' jet.conf)

    echo
    echo "    Checking if your Jet Bridge instance is registered..."
    echo

docker rm --force jet_bridge &> /dev/null
docker run \
    -p ${PORT}:8888 \
    --name=jet_bridge \
    -it \
    -v $(pwd):/jet \
    -e DATABASE_HOST=host.docker.internal \
    -e ARGS=token \
    jetadmin/jetbridge

echo
echo "    Starting Jet Bridge on port ${PORT}"

docker rm --force jet_bridge &> /dev/null
docker run \
    -p 8888:8888 \
    --name=jet_bridge \
    -v $(pwd):/jet \
    -d \
    jetadmin/jetbridge \
    &> /dev/null

echo "    Jet Bridge is now running and will run in startup"
echo
echo "    To stop run:"
echo "        docker stop jet_bridge"
echo
echo "    To start run:"
echo "        docker start jet_bridge"
echo
