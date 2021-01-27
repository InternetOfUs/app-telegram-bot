from __future__ import absolute_import, annotations

import logging.config
import os

from ask_for_help_bot.handler import AskForHelpHandler
from chatbot_core.translator.translator import Translator
from chatbot_core.v3.connector.social_connectors.telegram_connector import TelegramSocialConnector
from chatbot_core.v3.handler.event_dipatcher import MultiThreadEventDispatcher
from chatbot_core.v3.handler.instance_manager import InstanceManager
from common.logging_config import get_logging_configuration
from uhopper.utils.alert import AlertModule
from uhopper.utils.mqtt import MqttSubscriptionHandler

logging.config.dictConfig(get_logging_configuration("wenet-ask-for-help-chatbot"))
logger = logging.getLogger("uhopper.chatbot.wenet-ask-for-help-chatbot")

if __name__ == "__main__":
    topic = os.getenv("MQTT_TOPIC")
    subscriber = MqttSubscriptionHandler(os.getenv("MQTT_HOST"), os.getenv("MQTT_SUBSCRIBER_ID"),
                                         os.getenv("MQTT_USER"), os.getenv("MQTT_PASSWORD"))
    subscriber.add_subscription(topic)
    instance_namespace = os.getenv("INSTANCE_NAMESPACE")
    bot_token = os.getenv("TELEGRAM_KEY")
    connector = TelegramSocialConnector(bot_token)
    alert_module = AlertModule("wenet-ask-for-help-chatbot")
    alert_module.with_slack(["@nicolo.pomini"])
    wenet_backend_url = os.getenv("WENET_BACKEND_URL")
    wenet_hub_url = os.getenv("WENET_HUB_URL")
    app_id = os.getenv("WENET_APP_ID")
    task_type_id = os.getenv("TASK_TYPE_ID")
    wenet_authentication_url = os.getenv("WENET_AUTHENTICATION_URL")
    redirect_url = os.getenv("REDIRECT_URL")
    client_secret = os.getenv("CLIENT_SECRET")
    wenet_authentication_management_url = os.getenv("WENET_AUTHENTICATION_MANAGEMENT_URL")

    translation_folder_path = os.getenv("TRANSLATION_FOLDER_PATH", "../../translations")
    translator = Translator("wenet-ask-for-help", alert_module, translation_folder_path, fallback=False)
    translator.with_language("en", is_default=True, aliases=["en_US", "en_GB"])

    handler = AskForHelpHandler(
        instance_namespace,
        "wenet-ask-for-help",
        "wenet-ask-for-help-handler",
        bot_token,
        wenet_backend_url,
        wenet_hub_url,
        app_id,
        client_secret,
        redirect_url,
        wenet_authentication_url,
        wenet_authentication_management_url,
        task_type_id,
        alert_module,
        connector,
        None,
        translator
    )
    instance_manager = InstanceManager(instance_namespace, subscriber, MultiThreadEventDispatcher())
    instance_manager.with_event_handler(handler)

    try:
        instance_manager.start()
    except KeyboardInterrupt:
        subscriber.disconnect()
