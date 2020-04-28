#!/bin/bash

docker run --rm ${REGISTRY}/${IMAGE_NAME} ./run_tests.sh
if [ $? != 0 ]; then
    echo "ERR: One or more tests are failing"
    exit 1
fi