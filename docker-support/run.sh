#!/bin/bash

SCRIPT_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )

echo "Running pre-flight checks..."

SERVICE=$1


if [[ ${SERVICE} == "ws" ]]; then
    echo "Running ws..."
    ${SCRIPT_DIR}/run_ws.sh

elif [[ ${SERVICE} == "eat-together-bot" ]]; then
    echo "Running eat-together-bot..."
    ${SCRIPT_DIR}/run_eat-together-bot.sh

elif [[ ${SERVICE} == "ask-for-help-bot" ]]; then
    echo "Running ask-for-help-bot..."
    ${SCRIPT_DIR}/run_ask-for-help-bot.sh

else
    echo "Unknown service ${1}"
fi
