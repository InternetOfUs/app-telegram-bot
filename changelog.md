# Wenet bots - Changelog

# Versions

## 1.0.12
- Added sentry integration

## 1.0.10
- Changed the `project` field in the messages logged into the Wenet platform. Now the `appId` is used, instead of the `PROJECT_NAME` environment variable

## 1.0.9
- Added a new message promoting badges that appears after the login with Wenet
- Updated some translations in spanish and danish

## 1.0.8
- Updated spanish translations

## 1.0.7
- Fixed a bug in showing markdown characters into markdown messages

## 1.0.6
- Updated text of english messages with the new translations provided by Peter

## 1.0.5
* Removed redundant messages.
* Added new logic allowing to clean context once new messages from WeNet are received.
* Added support for "answer picked" notification message.
* Added support for "textual message" notification message.

## 1.0.4
- Several small fixes, such as typos, removal of the command `/profile` and `/report`
- Added the possibility to use an environment variable to set the time to live of the cached locale of each user
- Updated chatbot core to version `1.4.2`
- Added the possibility to use an environment variable to set the name of the log file, as well as the `project` value used in the logging component

## 1.0.3
- Updated the wenet common models to version `1.0.2`, that contain a major bug fix on OAuth token refresh

## 1.0.2
- Added language support
- Added caching system relying on Redis, to allow users to click on all the buttons
- Added logging of messages on the Wenet log component

## 1.0.1
- Removed a duplicated environment variable
- Fixed docker support

## 1.0.0
- First release of the _Eat together bot_, that allows users to create shared meals and to participate to them.
