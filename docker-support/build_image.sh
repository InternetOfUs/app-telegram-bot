#!/bin/bash

DEFAULT_VERSION="latest"





clean () {
    echo "Cleaning."
    rm -R -f ${SCRIPT_DIR}/src
    rm -R -f ${SCRIPT_DIR}/documentation
    rm -R ${SCRIPT_DIR}/requirements.txt
    rm -R ${SCRIPT_DIR}/translations

    rm -R ${SCRIPT_DIR}/test

    rm -R ${SCRIPT_DIR}/wenet-common-models-requirements.txt
    rm -R ${SCRIPT_DIR}/chatbot-core-requirements.txt
    rm -R ${SCRIPT_DIR}/utils-requirements.txt
}

SCRIPT_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
PROJECT_DIR=${SCRIPT_DIR}/..

mkdir ${SCRIPT_DIR}/src
cp -R ${PROJECT_DIR}/src/* ${SCRIPT_DIR}/src
mkdir ${SCRIPT_DIR}/documentation
cp -R ${PROJECT_DIR}/documentation/* ${SCRIPT_DIR}/documentation
cp ${PROJECT_DIR}/requirements.txt ${SCRIPT_DIR}

cp -r ${PROJECT_DIR}/translations ${SCRIPT_DIR}/translations

mkdir ${SCRIPT_DIR}/test
cp -R ${PROJECT_DIR}/test/* ${SCRIPT_DIR}/test

cp -R ${PROJECT_DIR}/wenet-common-models/src/* ${SCRIPT_DIR}/src
cp -R ${PROJECT_DIR}/wenet-common-models/requirements.txt ${SCRIPT_DIR}/wenet-common-models-requirements.txt

cp -R ${PROJECT_DIR}/chatbot-core/src/* ${SCRIPT_DIR}/src
cp -R ${PROJECT_DIR}/chatbot-core/requirements.txt ${SCRIPT_DIR}/chatbot-core-requirements.txt

cp -R ${PROJECT_DIR}/chatbot-core/utils-py/src/* ${SCRIPT_DIR}/src
cp -R ${PROJECT_DIR}/chatbot-core/utils-py/requirements.txt ${SCRIPT_DIR}/utils-requirements.txt


# Building image
GIT_REF=`git rev-parse --short HEAD`
docker build --build-arg GIT_REF=${GIT_REF} --cache-from ${REGISTRY}/${IMAGE_NAME} -t ${IMAGE_NAME} ${SCRIPT_DIR}
if [[ $? == 0 ]]; then
    echo "Build successful: ${IMAGE_NAME}."

    # Tagging images for registry
    echo "Tagging image for push to ${REGISTRY}."
    docker tag ${IMAGE_NAME} ${REGISTRY}/${IMAGE_NAME}
    echo "Image can be pushed with:"
    echo "  docker push ${REGISTRY}/${IMAGE_NAME}"

    # Cleaning
    clean

    exit 0

else
    echo "Error: Build failed for ${IMAGE_NAME}."

    # Cleaning
    clean

    exit 1
fi
