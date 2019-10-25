#!/bin/sh
set -e

# Jet Bridge
# https://github.com/jet-admin/jet-bridge
#
# This script is meant for quick & easy install via:
#
#   sh <(curl -s https://raw.githubusercontent.com/jet-admin/jet-bridge/dev/install_jet.sh)


remove_container() {
    docker rm --force ${CONTAINER_NAME} &> /dev/null || true
}

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
docker info &> /dev/null && { docker_state=1; } || { docker_state=0; }

if [ $docker_state != 1 ]; then
    echo
    echo "ERROR:"
    echo "    Docker does not seem to be running, run it first and retry"
    echo
    exit 1
fi

echo
echo "    Fetching latest Jet Bridge image..."
echo
docker pull jetadmin/jetbridge:dev

CONFIG_FILE="${PWD}/jet.conf"

echo
echo "    Installing Jet Bridge as a Docker container..."
echo

read -p "Enter Docker container name or leave default [jet_bridge]: " CONTAINER_NAME
CONTAINER_NAME=${CONTAINER_NAME:-jet_bridge}

# Checking if config file exists
if [ -f "$CONFIG_FILE" ]; then
    echo
    echo "    There is an existing config file will be used:"
    echo "    ${CONFIG_FILE}"
    echo "    You can edit it to change settings"
    echo
else
    remove_container
    docker run \
        --name=${CONTAINER_NAME} \
        -it \
        -v $(pwd):/jet \
        -e DATABASE_HOST=host.docker.internal \
        -e ARGS=config \
        jetadmin/jetbridge:dev
fi

PORT=$(awk -F "=" '/^PORT=/ {print $2}' jet.conf)

echo
echo "    Checking if your Jet Bridge instance is registered, please wait..."
echo


remove_container
docker run \
    --name=${CONTAINER_NAME} \
    -it \
    -v $(pwd):/jet \
    -e ARGS=check_token \
    jetadmin/jetbridge:dev

echo
echo "    Starting Jet Bridge..."
echo

# docker rm --force ${CONTAINER_NAME} &> /dev/null || true
remove_container
docker run \
    -p ${PORT}:${PORT} \
    --name=${CONTAINER_NAME} \
    -v $(pwd):/jet \
    -d \
    jetadmin/jetbridge:dev \
    1> /dev/null

echo "    To stop:"
echo "        docker stop ${CONTAINER_NAME}"
echo
echo "    To start:"
echo "        docker start ${CONTAINER_NAME}"
echo
echo "    To view logs:"
echo "        docker logs -f ${CONTAINER_NAME}"
echo
echo "    To view token:"
echo "        docker exec -it ${CONTAINER_NAME} jet_bridge token"
echo
echo "    Success! Jet Bridge is now running and will start automatically on system reboot"
echo
echo "    Port: ${PORT}"
echo "    Docker Container: ${CONTAINER_NAME}"
echo "    Config File: ${CONFIG_FILE}"
echo
