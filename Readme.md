# _Let's eat together_ chatbot

## Introduction
These chatbots are created in the context of `WeNet: the Internet of us`.

These Telegram chatbots are the first wenet application, allowing users to communicate with each other to organize shared meals with potential unknown people, or to ask questions and generic help, in a strong privacy-oriented manner.

The _eat-together_ bot allows users to create a new _task_, representing a shared meal. The WeNet platform will select some users potentially interested in the newly created task, and the bot will ask them to candidate to participate to it. Subsequently, the task creator will be notified of a candidature, being asked whether to accept or reject it. Candidates will acknowledge the owner's decision. Eventually, the task is closed by the owner using the chatbot, providing also an outcome, either successfully or failed.

The _ask-for-help_ bot allows to create _tasks_ that are questions, to which other Wenet users will answer.

The bots expose an HTTP endpoint to receive messages and notifications from the WeNet platform.

## Documentation
### How the bots work? High-level overview
The bots are _deterministic finite automatas_ (DFA), that are graphs where each node is a possible _state_ in which the conversation can be, and the edges are the _transactions_ between two states. For example:
1. The bot is in its initial state `S0`, which means that the user has not used it yet.
2. The user uses the `/start` command: this is a transaction, going from the initial state `S0` to the next state `S1`.
3. State `S1` proposes a message with 3 buttons: `B1`, `B2` and `B3`; each button makes the state change to a different state.
4. So we can have 3 transactions exiting from `S1`: the one triggered by `B1`, the one triggered by `B2` and the one triggered by `B3`.
5. Each transaction makes the user land into a state, either `S2`, `S3` or `S4`.

So the next state `S_(i + 1)` depends from the current state `S_(i)` and from the input received by the bot.

#### How the DFA is implemented?
The `WenetEventHandler` is an abstract class containing the common things used by the two _real_ handlers of the two bots, including the management of the DFA. 

The current state is saved in the user context, using as key the constant `self.CONTEXT_CURRENT_STATE`, while the value represents the state itself. Of course the value must be unique for each possible state of the bot, so it can be useful to define each possible state as constant in the handler class.

Every exchange of message between the user and the bot implies a change of state, so every time the context must be updated. 
Any possible additional piece of information needed to continue the conversation flow must be saved in the context. 
For example, to create a new taks the user must specify several information (a date, a title, a description, etc): 
all these data points are collected in several steps, each one represented by a state, and saving every time the user's inputs in the context. 
Only in the final state, the task is created and saved.

Assuming that we are in a state where we are expecting that the user types the name of the task, we know that the next input coming from the user will be the name of the task, and so we can use the intent manager to route the flow of the bot.
For example, the following piece of code calls the function `self.organize_q2` passing to it the intent `self.ORGANIZE_Q2`, and calling it every time an input is received and the current state is equal to `self.ORGANIZE_Q1`.
```python
self.intent_manager.with_fulfiller(
    IntentFulfillerV3(self.ORGANIZE_Q2, self.organize_q2).with_rule(
        static_context=(self.CONTEXT_CURRENT_STATE, self.ORGANIZE_Q1))
)
```

### Messages from Wenet
The bots can receive messages from the Wenet platform (notifications, textual messages, etc). Some methods are already available in the wenet handler to manage these situations:
- `handle_wenet_textual_message()` is triggered every time a `TextualMessage` is sent to the bot;
- `handle_wenet_authentication_result()` is triggered every time an user performs the authentication in the Wenet Hub;
- `handle_wenet_message()` is triggered in all the remaining cases, so when the message from Wenet is neither a `TextualMessage` nor a `WeNetAuthenticationEvent`; each application implements its own custom messages, and this is the place to handle them.

In these cases the messages are sent directly to the bot, without passing through the chatbot interface. So the user context must be explicitly fetched, together with the user information:
1. Get the user account related with the receiver id of the message:
```python
user_accounts = self.get_user_accounts(message.receiver_id)
if len(user_accounts) != 1:
    raise Exception(f"No context associated with Wenet user {message.receiver_id}")

user_account = user_accounts[0]
```
2. Get the context (it comes for free):
```python
context = user_account.context
```
3. Instanciate the service API:
```python
service_api = self._get_service_api_interface_connector_from_context(context)
```
The service API handler manages the OAuth tokens, so every time it is invoked is safe to call the following instruction to save the updated token:
```python
context = self._save_updated_token(context, service_api.client)
```
4. At the end, a `NotificationEvent` must be returned:
```python
return NotificationEvent(user_account.social_details, response_list, context)
```
where `response_list` is a list of `ResponseMessage` objects.

## Setup and configuration

### Installation
The chatbot required Python version 3.7 or higher.

All required Python packages can be installed using the command:

```bash
pip install -r requirements.txt
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

In order to run the _eat-together_ chatbot, do the following:
```bash
python -m eat_together_bot.main
```

In order to run the _ask-for-help_ chatbot, do the following:
```bash
python -m ask_for_help_bot.main
```

To run the endpoint:
```bash
python -m messages.main
```

### Chatbot env variables
Both the chatbots use the following environment variables

* `TELEGRAM_KEY`: secret key provided by Telegram to use the bot API
* `MQTT_HOST`: MQTT host
* `MQTT_SUBSCRIBER_ID`: MQTT subscriber id for the client
* `MQTT_USER`: MQTT user
* `MQTT_PASSWORD`: MQTT password
* `MQTT_TOPIC`: MQTT topic to listen on
* `INTERFACE_APIKEY`: bot interface api key
* `INSTANCE_NAMESPACE`: bot instance namespace
* `WENET_INSTANCE_URL`: the url of the WeNet instance
* `WENET_APP_ID`: WeNet App ID used by the bot
* `WENET_HUB_URL`: url of the WeNet hub
* `TASK_TYPE_ID`: the type ID of the tasks
* `COMMUNITY_ID`: the community ID
* `MAX_USERS`: the maximum number of users that should receive the question in the ask4help bot (default is 5)
* `SURVEY_URL`: the url of the survey
* `PILOT_HELPER_URL`: (Optional) the url of the helper page specific for a pilot
* `CLIENT_SECRET`: the secret key of the WeNet application
* `WENET_AUTHENTICATION_MANAGEMENT_URL`: the URL that manages OAuth in WeNet
* `REDIRECT_URL`: the redirection URL associated with the WeNet application
* `PROJECT_NAME` (optional): a string that will be used as name of the log file (with the format `<PROJECT_NAME>.log`). The default value is `wenet-ask-for-help-chatbot`
* `LOCALE_TTL` (optional): the time to live of the Redis key in which the user locale is saved, in seconds. By default, it is 86400 (24h).
* `SENTRY_DSN`: (Optional) The data source name for sentry, if not set the project will not create any event
* `SENTRY_RELEASE`: (Optional) If set, sentry will associate the events to the given release
* `SENTRY_ENVIRONMENT`: (Optional) If set, sentry will associate the events to the given environment (ex. `production`, `staging`)

For the translations of the badges messages the following environment variables are needed:
* `FIRST_QUESTION_BADGE_ID`: the id of the first question badge
* `CURIOUS_LEVEL_1_BADGE_ID`: the id of the curious level 1 badge
* `CURIOUS_LEVEL_2_BADGE_ID`: the id of the curious level 2 badge
* `FIRST_ANSWER_BADGE_ID`: the id of the first answer badge
* `HELPER_LEVEL_1_BADGE_ID`: the id of the helper level 1 badge
* `HELPER_LEVEL_2_BADGE_ID`: the id of the helper level 2 badge
* `FIRST_GOOD_ANSWER_BADGE_ID`: the id of the first good answer badge
* `GOOD_ANSWERS_LEVEL_1_BADGE`: the id of the good answerer level 1 badge
* `GOOD_ANSWERS_LEVEL_2_BADGE`: the id of the good answerer level 2 badge
* `FIRST_LONG_ANSWER_BADGE_ID`: the id of the first long answer badge
* `EXPLAINER_LEVEL_1_BADGE_ID`: the id of the explainer level 1 badge
* `EXPLAINER_LEVEL_2_BADGE_ID`: the id of the explainer level 2 badge

Optional variables (to setup Redis):
- `REDIS_HOST` (default is `localhost`)
- `REDIS_PORT` (default is 6379)
- `REDIS_DB` (default is 0)

The _ask for help_ bot has the following optional environment variable:
* `TRANSLATION_FOLDER_PATH`, indicating the path of the folder in which translations are stored (default is `../../translations`).

### Endpoint env variables

* `MESSAGES_HOST`: host running the APIs (default to `0.0.0.0`)
* `MESSAGES_PORT`: port of the host (default to `12345`)
* `MQTT_HOST`: MQTT host
* `MQTT_PUBLISHER_ID`: MQTT publisher id for the client
* `MQTT_USER`: MQTT user
* `MQTT_PASSWORD`: MQTT password
* `MQTT_TOPIC`: MQTT topic to write on
* `INSTANCE_NAMESPACE`: bot instance namespace
* `WENET_APP_ID`: WeNet App ID used by the bot
* `WENET_HUB_URL`: url of the WeNet hub
* `BOT_ID`: the bot ID associated with the EventHandler used by the bot itself.
* `PROJECT_NAME` (optional): a string that will be used as name of the log file (with the format `<PROJECT_NAME>-messages.log`). The default value is `wenet-ask-for-help-chatbot`.

## Instances

The development instance of this chatbot is available here [https://t.me/wenet_test_bot](https://t.me/wenet_test_bot)
The production instance is available here [https://t.me/wenet_eat_together_bot](https://t.me/wenet_eat_together_bot)

## Maintainers

- Nicolò Pomini (nicolo.pomini@u-hopper.com)
- Carlo Caprini (carlo.caprini@u-hopper.com)
- Stefano Tavonatti (stefano.tavonatti@u-hopper.com)
