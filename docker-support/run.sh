#!/bin/bash

echo "Verifying env variables presence"
declare -a REQUIRED_ENV_VARS=()

for e in "${REQUIRED_ENV_VARS[@]}"
do
    if [ -z "$e" ]; then
        echo >&2 "Required env variable is missing"
        exit 1
    fi
done

DEFAULT_WORKERS=4
if [ -z "${WORKERS}" ]; then
    WORKERS=$DEFAULT_WORKERS
fi

if [ $1 == "bots" ]; then
    exec python -m eat_together_bot.main
else
  if [ $1 == "ws" ]; then
    echo "Running ws"
    # exec gunicorn -w "${WORKERS}" -b 0.0.0.0:80 "" # TODO gunicorn
    exec python -m messages.main

  else
    echo "Missing argument, use:"
    echo "  ./run.sh bots - for running the bots"
    echo "  ./runs.sh ws - to run the webservices"
    exit 1
  fi

fi
