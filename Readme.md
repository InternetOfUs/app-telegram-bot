# _Let's eat together_ chatbot

## Introduction
This chatbot is created in the context of `WeNet: the Internet of us`.

This Telegram chatbot is the first wenet application, allowing users to communicate with each other to organize shared meals with potential unknown people, in a strong privacy-oriented manner.

The bot allows users to create a new _task_, representing a shared meal. The WeNet platform will select some users potentially interested in the newly created task, and the bot will ask them to candidate to participate to it. Subsequently, the task creator will be notified of a candidature, being asked whether to accept or reject it. Candidates will acknowledge the owner's decision. Eventually, the task is closed by the owner using the chatbot, providing also an outcome, either successfully or failed. 

The bot exposes an HTTP endpoint to receive messages and notifications from the WeNet platform.

## Setup and configuration

### Installation
The chatbot required Python version 3.7 or higher.

The project requires some submodules that can be configured by running the command

```bash
git submodule update --init --recursive
```

All required Python packages can be installed using the command

```bash
pip install -r requirements.txt
pip install -r wenet-common-models/requirements.txt
pip install -r chatbot-core/requirements.txt
pip install -r chatbot-core/utils-py/requirements.txt
```

### Docker support

A dedicated Docker image for this component can be build by taking advantage of the repository Docker support.
The command:
```bash
./build_docker_image.sh
```
will:

* run the tests on the checked-out version of the service APIs;
* build the docker image for the chatbot (the naming is the following `registry.u-hopper.com/`)

## Usage

In order to run the chatbot, do the following:
```bash
python -m eat_together_bot.main
```

To run the endpoint:
```bash
python -m messages.main
```

### Chatbot env variables

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

### Endpoint env variables

* `MESSAGES_HOST`: host running the APIs (default to `0.0.0.0`)
* `MESSAGES_PORT`: port of the host (default to `12345`)
* `MQTT_HOST`: MQTT host
* `MQTT_SUBSCRIBER_ID`: MQTT publisher id for the client
* `MQTT_USER`: MQTT user
* `MQTT_PASSWORD`: MQTT password
* `MQTT_TOPIC`: MQTT topic to write on
* `INSTANCE_NAMESPACE`: bot instance namespace

## Instances

The development instance of this chatbot is available here [https://t.me/wenet_test_bot](https://t.me/wenet_test_bot)

## Maintainers

- Nicolò Pomini (nicolo.pomini@u-hopper.com)
- Carlo Caprini (carlo.caprini@u-hopper.com)
- Stefano Tavonatti (stefano.tavonatti@u-hopper.com)
