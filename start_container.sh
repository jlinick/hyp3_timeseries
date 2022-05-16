#!/bin/bash

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
source ${SCRIPT_DIR}/configs

# docker product directory
DOCKER_PRODUCT_DIR='/products'

# output products/working directory
SHAPEFILE_FILENAME=$(basename "${SHAPEFILE_PATH}")
LOCAL_DATA_DIR=$(dirname "${SHAPEFILE_PATH}")
DOCKER_DATA_DIR='/data'
DOCKER_SHAPEFILE_PATH="/data/${SHAPEFILE_FILENAME}"

# code repository inside the docker container
DOCKER_CODE_DIR='/thwaites_timeseries'

build_dockerfile() {
    cd "${SCRIPT_DIR}"
    if [[ "$(docker images -q thwaites_timeseries:latest 2> /dev/null)" == "" ]]; then
        echo "thwaites_timeseries docker image does not exist, building..."
	docker build -t "thwaites_timeseries:latest" -f "${SCRIPT_DIR}/docker/Dockerfile" .	
    else
        echo "thwaites_timeseries dockerfile exists."
    fi
}

build_dockerfile

docker run --rm -ti -v ~/.netrc:/workdir/.netrc:ro -v ${LOCAL_DATA_DIR}:${DOCKER_DATA_DIR}:ro -v ${SCRIPT_DIR}:${DOCKER_CODE_DIR} -v ${LOCAL_PRODUCT_DIR}:${DOCKER_PRODUCT_DIR} thwaites_timeseries:latest /bin/bash #/thwaites_timeseries/run.sh

