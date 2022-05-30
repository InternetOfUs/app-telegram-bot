# Changelog

## Version 3.*

### 3.0.0
- Added support for task expiration callbacks
- Added support for liking preferred answer
- Added support for showing received answers in batches
- Added support for publishing answers in a preferred way (e.g., Anonymously) or not publishing them

## Version 2.*

### 2.2.0

:rocket: New features
- Delayed platform messages so that the in-app message exchange does not get interrupted
- Delayed remind me later messages so that the in-app message exchange does not get interrupted
- Added question in the flow for accepting the answer for publishing questions and best answers in a dedicated telegram channel

:house: Internal
- Updated Chatbot Core to version `1.5.3`

### 2.1.1
- Updated translations
- Updated to Project template version `4.6.1`

### 2.1.0
- Updated translations and added support for translation of badges messages
- Integrated a different conduct message using helper url specific for a pilot if specified in the env vars
- Modified rhe reminder to the user of the attributes he chose when accepting the question

### 2.0.3
- Fixed non-ascii characters are not rendered correctly, json.dumps is applied to user texts and json.loads is applied to platform texts
- Reversed the order of the buttons of the sensitive question
- Reminded to the user the attributes he chose when accepting the question

### 2.0.2
- Updated translations
- Fixed Emojis are not rendered correctly, demojize is applied to user texts and emojize is applied to platform texts
- Added code of conduct message to the start messages
- Updated to project template `4.6.0`

### 2.0.1
- Refactored PendingMessagesJob handling errors and deleting messages that cause these errors

### 2.0.0
- Integrated position data in the question and answer flow
- Integrated sensitive and anonymous information data in the question and answer flow
- Updated to project template `4.5.1`
- Removed submodules and added the libraries as packages:
  - `uhopper-chatbot` version `1.5.2`;
  - `wenet-common` version `3.1.0`;
  - `uhopper-alert` version `2.0.0`;
  - `uhopper-mqtt` version `1.1.0`.
- Updated question flow adding social closeness input in the question creation flow instead of similarity and reason
- Integrated domain data in the question flow
- Integrated domain similarity data in the question flow
- Added environment variables for communityId and maxUsers fields
- Integrated belief and values similarity data in the question flow
- Updated app commands: renamed `/question` into `/ask` and `/answer` into `/questions`
- Integrated rating flow when accepting an answer
- Updated common models to fix service APIs methods for getting all tasks of an application and for an user
- Integrated new structures of the callback messages
- Refactored PendingMessagesJob
- Added `/badges` command to request insights on badge status
- Added a survey promo message in the welcome messages

## Version 1.*

### 1.0.12
- Added sentry integration

### 1.0.11
- Updated common models to hotfix for badges messages

### 1.0.10
- Changed the `project` field in the messages logged into the Wenet platform. Now the `appId` is used, instead of the `PROJECT_NAME` environment variable

### 1.0.9
- Added a new message promoting badges that appears after the login with Wenet
- Updated some translations in spanish and danish

### 1.0.8
- Updated spanish translations

### 1.0.7
- Fixed a bug in showing markdown characters into markdown messages

### 1.0.6
- Updated text of english messages with the new translations provided by Peter

### 1.0.5
- Removed redundant messages.
- Added new logic allowing to clean context once new messages from WeNet are received.
- Added support for "answer picked" notification message.
- Added support for "textual message" notification message.

### 1.0.4
- Several small fixes, such as typos, removal of the command `/profile` and `/report`
- Added the possibility to use an environment variable to set the time to live of the cached locale of each user
- Updated chatbot core to version `1.4.2`
- Added the possibility to use an environment variable to set the name of the log file, as well as the `project` value used in the logging component

### 1.0.3
- Updated the wenet common models to version `1.0.2`, that contain a major bug fix on OAuth token refresh

### 1.0.2
- Added language support
- Added caching system relying on Redis, to allow users to click on all the buttons
- Added logging of messages on the Wenet log component

### 1.0.1
- Removed a duplicated environment variable
- Fixed docker support

### 1.0.0
- First release of the _Eat together bot_, that allows users to create shared meals and to participate to them.
