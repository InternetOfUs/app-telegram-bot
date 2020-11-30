#!/bin/bash

DEFAULT_VERSION="1.0.0"

clean () {
    rm -R -f ${SCRIPT_DIR}/src
    rm -R ${SCRIPT_DIR}/requirements.txt
    rm -R ${SCRIPT_DIR}/test
    rm -R ${SCRIPT_DIR}/requirements-common.txt
}

SCRIPT_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
PROJECT_DIR=${SCRIPT_DIR}/..
CORE_BUILD_DIR=${PROJECT_DIR}/chatbot-core/docker-support/core

# Identifying build version

mkdir ${SCRIPT_DIR}/src
mkdir ${SCRIPT_DIR}/test
cp -R ${PROJECT_DIR}/src/* ${SCRIPT_DIR}/src
cp ${PROJECT_DIR}/requirements.txt ${SCRIPT_DIR}
cp -R ${PROJECT_DIR}/test/* ${SCRIPT_DIR}/test
cp -R ${PROJECT_DIR}/wenet-common-models/src/* ${SCRIPT_DIR}/src
cp -R ${PROJECT_DIR}/wenet-common-models/test/* ${SCRIPT_DIR}/test
cp ${PROJECT_DIR}/wenet-common-models/requirements.txt ${SCRIPT_DIR}/requirements-common.txt



echo "Building core"
${CORE_BUILD_DIR}/runner.sh -b
if [ $? != 0 ]; then
    echo "Error: Unable to core image"
    clean
    exit 1
fi

# Building image

docker build -t ${IMAGE_NAME} ${SCRIPT_DIR}
if [ $? == 0 ]; then

    echo "Build successful: ${IMAGE_NAME}"

    # Tagging images for registry

    echo "Tagging image for push to registry.u-hopper.com"
    docker tag ${IMAGE_NAME} ${REGISTRY}/${IMAGE_NAME}
    echo "Image can be pushed with:"
    echo "- docker push registry.u-hopper.com/${IMAGE_NAME}"
    # Cleaning
    clean

    exit 0

else
    echo "ERR: Build failed for ${IMAGE_NAME}"
    # Cleaning
    clean

    exit 1
fi

