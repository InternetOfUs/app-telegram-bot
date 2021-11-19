from __future__ import absolute_import, annotations

import logging.config
import os
import sentry_sdk

from ask_for_help_bot.handler import AskForHelpHandler
from chatbot_core.translator.translator import Translator
from chatbot_core.v3.connector.social_connectors.telegram_connector import TelegramSocialConnector
from chatbot_core.v3.handler.event_dipatcher import MultiThreadEventDispatcher
from chatbot_core.v3.handler.instance_manager import InstanceManager
from common.logging_config import get_logging_configuration
from uhopper.utils.alert.module import AlertModule
from uhopper.utils.mqtt.handler import MqttSubscriptionHandler
from sentry_sdk.integrations.logging import LoggingIntegration

logging.config.dictConfig(get_logging_configuration(os.getenv("PROJECT_NAME", "wenet-ask-for-help-chatbot")))
logger = logging.getLogger("uhopper.chatbot.wenet-ask-for-help-chatbot")

sentry_logging = LoggingIntegration(
    level=logging.INFO,  # Capture info and above as breadcrumbs
    event_level=logging.ERROR  # Send errors as events
)

sentry_sdk.init(
    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for performance monitoring.
    # We recommend adjusting this value in production.
    traces_sample_rate=1.0
)

if __name__ == "__main__":
    topic = os.getenv("MQTT_TOPIC")
    subscriber = MqttSubscriptionHandler(os.getenv("MQTT_HOST"), os.getenv("MQTT_SUBSCRIBER_ID"),
                                         os.getenv("MQTT_USER"), os.getenv("MQTT_PASSWORD"))
    subscriber.add_subscription(topic)
    instance_namespace = os.getenv("INSTANCE_NAMESPACE")
    bot_token = os.getenv("TELEGRAM_KEY")
    connector = TelegramSocialConnector(bot_token)
    alert_module = AlertModule("wenet-ask-for-help-chatbot")
    wenet_instance_url = os.getenv("WENET_INSTANCE_URL")
    wenet_hub_url = os.getenv("WENET_HUB_URL")
    app_id = os.getenv("WENET_APP_ID")
    task_type_id = os.getenv("TASK_TYPE_ID")
    community_id = os.getenv("COMMUNITY_ID")
    max_users = int(os.getenv("MAX_USERS", 5))
    survey_url = os.getenv("SURVEY_URL")
    helper_url = os.getenv("PILOT_HELPER_URL")
    wenet_authentication_url = os.getenv("WENET_AUTHENTICATION_URL")
    redirect_url = os.getenv("REDIRECT_URL")
    client_secret = os.getenv("CLIENT_SECRET")
    wenet_authentication_management_url = os.getenv("WENET_AUTHENTICATION_MANAGEMENT_URL")

    translation_folder_path = os.getenv("TRANSLATION_FOLDER_PATH", "../../translations")
    translator = Translator("wenet-ask-for-help", alert_module, translation_folder_path, fallback=False)
    translator.with_language("en", is_default=True, aliases=["en_US", "en_GB"])
    translator.with_language("it", is_default=False, aliases=["it_IT", "it_CH"])
    # translator.with_language("da", is_default=False)
    translator.with_language("mn", is_default=False)
    translator.with_language("es", is_default=False, aliases=["es_ES", "es_PY", "es_AR", "es_MX"])

    handler = AskForHelpHandler(
        instance_namespace,
        "wenet-ask-for-help",
        "wenet-ask-for-help-handler",
        bot_token,
        wenet_instance_url,
        wenet_hub_url,
        app_id,
        client_secret,
        redirect_url,
        wenet_authentication_url,
        wenet_authentication_management_url,
        task_type_id,
        community_id,
        max_users,
        survey_url,
        helper_url,
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
