#!/bin/sh
set -e

# Jet Bridge
# https://github.com/jet-admin/jet-bridge
#
# This script is meant for quick & easy install via:
#
#   sh <(curl -s https://raw.githubusercontent.com/jet-admin/jet-bridge/dev/install_jet.sh)


TOKEN=$1

check_arguments() {
    if [[ -z $TOKEN ]]; then
        echo
        echo "ERROR:"
        echo "    Pass token as an argument"
        echo
        exit 1
    fi
}

remove_container() {
    docker rm --force ${CONTAINER_NAME} &> /dev/null || true
}

check_is_docker_installed() {
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
}

check_is_docker_running() {
    # Check if docker is running
    docker info &> /dev/null && { docker_state=1; } || { docker_state=0; }

    if [ $docker_state != 1 ]; then
        echo
        echo "ERROR:"
        echo "    Docker does not seem to be running, run it first and retry"
        echo
        exit 1
    fi
}

fetch_latest_jet_bridge() {
    echo
    echo "    Fetching latest Jet Bridge image..."
    echo

    docker pull jetadmin/jetbridge:dev
}

prepare_container() {
    echo
    echo "    Installing Jet Bridge as a Docker container..."
    echo

    read -p "Enter Docker container name or leave default [jet_bridge]: " CONTAINER_NAME
    CONTAINER_NAME=${CONTAINER_NAME:-jet_bridge}
}

create_config() {
    CONFIG_FILE="${PWD}/jet.conf"

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
            -e TOKEN=${TOKEN} \
            -e DATABASE_HOST=host.docker.internal \
            -e ARGS=config \
            -e ENVIRONMENT=jet_bridge_docker \
            --net=host \
            jetadmin/jetbridge:dev
    fi
}

check_token() {
    echo
    echo "    Checking if your Jet Bridge instance is registered, please wait..."
    echo

    remove_container
    docker run \
        --name=${CONTAINER_NAME} \
        -it \
        -v $(pwd):/jet \
        -e ARGS=check_token \
        -e ENVIRONMENT=jet_bridge_docker \
        --net=host \
        jetadmin/jetbridge:dev
}

run_instance() {
    PORT=$(awk -F "=" '/^PORT=/ {print $2}' jet.conf)

    echo
    echo "    Starting Jet Bridge..."

    # docker rm --force ${CONTAINER_NAME} &> /dev/null || true
    remove_container
    docker run \
        -p ${PORT}:${PORT} \
        --name=${CONTAINER_NAME} \
        -v $(pwd):/jet \
        -e ENVIRONMENT=jet_bridge_docker \
        --net=host \
        -d \
        jetadmin/jetbridge:dev \
        1> /dev/null

    BASE_URL="http://localhost:${PORT}/api/"
    REGISTER_URL="${BASE_URL}register/"

    printf '    '

    i=0
    DELAY=1
    TIMEOUT=10
    i_last=$((TIMEOUT / DELAY))

    until $(curl --output /dev/null --silent --fail ${BASE_URL}); do
        printf '.'
        sleep $DELAY
        (( count++ ))

        if [[ count -ge $i_last ]]; then
            echo
            echo
            echo "ERROR:"
            echo "    Jet Bridge failed to start after timeout (${TIMEOUT}):"
            echo

            docker logs ${CONTAINER_NAME}

            exit 1
        fi
    done

    if command -v python &>/dev/null; then
        python -mwebbrowser ${REGISTER_URL}
    fi

    echo
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
    echo "    Go to https://app.jetadmin.io/ to finish installation"
    echo
}

check_arguments
check_is_docker_installed
check_is_docker_running
fetch_latest_jet_bridge
prepare_container
create_config
#check_token
run_instance
