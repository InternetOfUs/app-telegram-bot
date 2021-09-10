#!/bin/bash

echo "Verifying env variables presence."
declare -a REQUIRED_ENV_VARS=(
                                "${TELEGRAM_KEY}"
                                "${MQTT_HOST}"
                                "${MQTT_SUBSCRIBER_ID}"
                                "${MQTT_USER}"
                                "${MQTT_PASSWORD}"
                                "${MQTT_TOPIC}"
                                "${INTERFACE_APIKEY}"
                                "${INSTANCE_NAMESPACE}"
                                "${WENET_INSTANCE_URL}"
                                "${WENET_APP_ID}"
                                "${WENET_HUB_URL}"
                                "${TASK_TYPE_ID}"
                                "${CLIENT_SECRET}"
                                "${WENET_AUTHENTICATION_MANAGEMENT_URL}"
                                "${REDIRECT_URL}"
                              )

for e in "${REQUIRED_ENV_VARS[@]}"
do
  if [[ -z "$e" ]]; then
    # TODO should print the missing variable
    echo >&2 "Error: A required env variable is missing."
    exit 1
  fi
done

echo "Running eat-together-bot..."

#
# Important note: env variables should not be passed as arguments to the module!
# This will allow for an easier automatisation of the docker support creation.
#


exec python -m eat_together_bot.main
