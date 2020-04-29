# Let's eat together chatbot

This chatbot is created in the context of `WeNet: the Internet of us`. It will be used in pilots for the taks _Let's eat together_, allowing people to organize lunches and dinners without knowing each other

## Chatbot env variables
* `TELEGRAM_KEY`: secret key provided by Telegram to use the bot API
* `MQTT_HOST`
* `MQTT_SUBSCRIBER_ID`
* `MQTT_USER`
* `MQTT_PASSWORD`
* `MQTT_TOPIC`
* `INTERFACE_APIKEY`
* `INSTANCE_NAMESPACE`
* `WENET_BACKEND_URL` (e.g https://wenet.u-hopper.com/service)
* `WENET_APP_ID`: WeNet App ID used by the bot
* `WENET_HUB_URL`: Landing page to make users log in into Wenet

## Endpoint env variables
* `MESSAGES_HOST`: host on which the endpoint for receiving messages from WeNet runs;
* `MESSAGES_PORT`: host on which the endpoint for receiving messages from WeNet runs;
* `MQTT_HOST`: same as before
* `MQTT_SUBSCRIBER_ID`: **different** with respect to the other one
* `MQTT_USER`: same as before
* `MQTT_PASSWORD`: same as before
* `MQTT_TOPIC`: same as before
* `INSTANCE_NAMESPACE`: same as before