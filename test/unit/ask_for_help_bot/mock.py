from __future__ import absolute_import, annotations

from chatbot_core.translator.translator import Translator
from chatbot_core.v3.connector.chatbot_interface import ChatbotInterfaceConnectorV3
from chatbot_core.v3.connector.social_connectors.telegram_connector import TelegramSocialConnector
from chatbot_core.v3.logger.event_logger import LoggerHandler
from uhopper.utils.alert.module import AlertModule
from uhopper.utils.language.detector import LanguageDetector
from wenet.storage.cache import InMemoryCache

from ask_for_help_bot.handler import AskForHelpHandler
from common.messages_to_log import LogMessageHandler


class MockAskForHelpHandler(AskForHelpHandler):

    def __init__(self) -> None:
        self._instance_namespace = "instance_namespace",
        self._bot_id = "wenet-ask-for-help",
        self._handler_id = "wenet-ask-for-help-handler",
        self._alert_module = AlertModule("wenet-ask-for-help-chatbot")
        self._nlp_handler = None
        self._translator = Translator("wenet-ask-for-help", self._alert_module, "translation_folder_path", fallback=False)
        self._delay_between_messages_sec = None
        self._delay_between_text_sec = None
        self._connector = TelegramSocialConnector("bot_token")
        self._interface_connector = ChatbotInterfaceConnectorV3("instance_namespace", "api_key", "host")
        self._language_detector = LanguageDetector.build()
        self._logger_handler = LoggerHandler(None)
        self.cache = InMemoryCache()
        self.oauth_cache = InMemoryCache()
        self.telegram_id = "bot_token"
        self.bot_username = "username"
        self.bot_name = "first_name"
        self.wenet_instance_url = "wenet_instance_url"
        self.wenet_hub_url = "wenet_hub_url"
        self.app_id = "app_id"
        self.client_secret = "client_secret"
        self.redirect_url = "redirect_url"
        self.wenet_authentication_url = "wenet_authentication_url"
        self.wenet_authentication_management_url = "wenet_authentication_management_url"
        self.task_type_id = "task_type_id"
        self.community_id = "community_id"
        self.max_users = 5
        self.survey_url = "survey_url"
        self.helper_url = "helper_url"
        self.channel_id = "channel_id"
        self.publication_language = "en"
        self.max_answers = 15
        self.expiration_duration = 1
        self.nearby_expiration_duration = 1
        self.message_parser_for_logs = LogMessageHandler(self.app_id, "Telegram")
