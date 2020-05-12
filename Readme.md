# Let's eat together chatbot

This chatbot is created in the context of `WeNet: the Internet of us`. It will be used in pilots for the taks _Let's eat together_, allowing people to organize lunches and dinners without knowing each other

## Chatbot env variables

* `TELEGRAM_KEY`: secret key provided by Telegram to use the bot API
* `MQTT_HOST`: MQTT host
* `MQTT_SUBSCRIBER_ID`: MQTT subscriber id for the client
* `MQTT_USER`: MQTT user
* `MQTT_PASSWORD`: MQTT password
* `MQTT_TOPIC`: MQTT topic to listen on
* `INTERFACE_APIKEY`: bot interface api key
* `INSTANCE_NAMESPACE`: bot instance namespace
* `WENET_BACKEND_URL`: the url to the WeNet Service APIs
* `WENET_APP_ID`: WeNet App ID used by the bot
* `WENET_HUB_URL`: url of the WeNet hub
* `TASK_TYPE_ID`: the type ID of the tasks Eat Together
* `API_KEY`: the API key to authenticate requests to the Service APIs

## Endpoint env variables

* `MESSAGES_HOST`: host running the APIs (default to `0.0.0.0`)
* `MESSAGES_PORT`: port of the host (default to `12345`)
* `MQTT_HOST`: MQTT host
* `MQTT_SUBSCRIBER_ID`: MQTT publisher id for the client
* `MQTT_USER`: MQTT user
* `MQTT_PASSWORD`: MQTT password
* `MQTT_TOPIC`: MQTT topic to write on
* `INSTANCE_NAMESPACE`: bot instance namespace