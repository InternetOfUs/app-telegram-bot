#!/bin/bash

python -m unittest discover test
if [ $? != 0 ]; then
    echo "ERR: Tests failed"
    exit 1
fi

