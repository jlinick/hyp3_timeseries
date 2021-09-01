#!/bin/bash

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# input data
LOCAL_PRODUCT_DIR='/home/jlinick/products/hyp3_timeseries'
DOCKER_PRODUCT_DIR='/products'

# output products/working directory
LOCAL_DATA_DIR='/home/jlinick/data/hyp3_timeseries'
DOCKER_DATA_DIR='/data'

# code repository inside the docker container
DOCKER_CODE_DIR='/hyp3_timeseries'

build_dockerfile() {
    cd "${SCRIPT_DIR}"
    if [[ "$(docker images -q tops:latest 2> /dev/null)" == "" ]]; then
        echo "hyp3_timeseries docker image does not exist, building..."
        docker build -t "hyp3_timeseries:latest" -f "docker/Dockerfile" .
    else
        echo "hyp3_timeseries dockerfile exists."
    fi
}

build_dockerfile

docker run --rm -ti -v ~/.netrc:/products/.netrc:ro -v ${LOCAL_DATA_DIR}:${DOCKER_DATA_DIR}:ro -v ${SCRIPT_DIR}:${DOCKER_CODE_DIR} -v ${LOCAL_PRODUCT_DIR}:${DOCKER_PRODUCT_DIR} hyp3_timeseries:latest

