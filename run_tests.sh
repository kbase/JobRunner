#!/bin/bash

# Java must be installed to run this script.
# For mac: https://www.oracle.com/java/technologies/downloads/#jdk24-mac

CROMWELL_JAR=cromwell-44.jar

uv sync --dev

if [ ! -f "$HOME"/"$CROMWELL_JAR" ]; then
    echo "Downloading Cromwell JAR file..."
    wget "https://github.com/broadinstitute/cromwell/releases/download/44/$CROMWELL_JAR" -O "$HOME/$CROMWELL_JAR"
else
    echo "Cromwell JAR file already exists, skipping download."
fi
touch "$HOME"/cromwell.conf

# uncomment this line and fill in the proper location for the docker socket if necessary
# export DOCKER_HOST=unix:///var/run/docker.sock:

# These must be set to a NON empty string or the tests will FAIL
export KB_AUTH_TOKEN="fake"
export KB_ADMIN_AUTH_TOKEN="fake"
# Must contain http
export KB_BASE_URL="https://ci.kbase.us/services/"

# Docker must be able to read these directories
export JOB_DIR=$(pwd)/test_jobdir
export KB_REF_DATA=$(pwd)/test_refdata

mkdir -p "$JOB_DIR"
mkdir -p "$KB_REF_DATA"

make mock
make testimage
make test
