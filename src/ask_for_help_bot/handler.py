from typing import Optional, List

from chatbot_core.model.event import IncomingSocialEvent
from chatbot_core.nlp.handler import NLPHandler
from chatbot_core.translator.translator import Translator
from chatbot_core.v3.connector.social_connector import SocialConnector
from chatbot_core.v3.logger.event_logger import LoggerConnector
from chatbot_core.v3.model.messages import TextualResponse, RapidAnswerResponse
from chatbot_core.v3.model.outgoing_event import OutgoingEvent, NotificationEvent
from common.wenet_event_handler import WenetEventHandler
from uhopper.utils.alert import AlertModule
from wenet.common.model.message.message import TextualMessage, TaskNotification, WeNetAuthentication


class AskForHelpHandler(WenetEventHandler):
    # all the recognize intents
    INTENT_QUESTION = '/question'

    def __init__(self, instance_namespace: str, bot_id: str, handler_id: str, telegram_id: str, wenet_backend_url: str,
                 wenet_hub_url: str, app_id: str, client_secret: str, redirect_url: str, wenet_authentication_url: str,
                 wenet_authentication_management_url: str, task_type_id: str, alert_module: AlertModule,
                 connector: SocialConnector, nlp_handler: Optional[NLPHandler], translator: Optional[Translator],
                 delay_between_messages_sec: Optional[int] = None, delay_between_text_sec: Optional[float] = None,
                 logger_connectors: Optional[List[LoggerConnector]] = None):
        super().__init__(instance_namespace, bot_id, handler_id, telegram_id, wenet_backend_url, wenet_hub_url, app_id,
                         client_secret, redirect_url, wenet_authentication_url, wenet_authentication_management_url,
                         task_type_id, alert_module, connector, nlp_handler, translator, delay_between_messages_sec,
                         delay_between_text_sec, logger_connectors)

    def _get_user_locale(self, incoming_event: IncomingSocialEvent) -> str:
        # TODO implement this
        return 'en'

    def _get_help_and_info_message(self, locale: str) -> str:
        return self._translator.get_translation_instance(locale).with_text("info_text").translate()

    def action_info(self, incoming_event: IncomingSocialEvent, intent: str) -> OutgoingEvent:
        user_locale = self._get_user_locale(incoming_event)
        response = OutgoingEvent(social_details=incoming_event.social_details)
        response.with_message(TextualResponse(self._get_help_and_info_message(user_locale)))
        return response

    def action_error(self, incoming_event: IncomingSocialEvent, intent: str) -> OutgoingEvent:
        user_locale = self._get_user_locale(incoming_event)
        response = OutgoingEvent(social_details=incoming_event.social_details)
        message = self._translator.get_translation_instance(user_locale).with_text("error_text").translate()
        response.with_message(TextualResponse(message))
        return response

    def cancel_action(self, incoming_event: IncomingSocialEvent, intent: str) -> OutgoingEvent:
        user_locale = self._get_user_locale(incoming_event)
        message = self._translator.get_translation_instance(user_locale).with_text("cancel_text").translate()
        response = OutgoingEvent(social_details=incoming_event.social_details)
        response.with_message(TextualResponse(message))
        return response

    def handle_help(self, message: IncomingSocialEvent, intent: str) -> OutgoingEvent:
        user_locale = self._get_user_locale(message)
        response = OutgoingEvent(social_details=message.social_details)
        response.with_message(TextualResponse(self._get_help_and_info_message(user_locale)))
        return response

    def action_start(self, incoming_event: IncomingSocialEvent, intent: str) -> OutgoingEvent:
        user_locale = self._get_user_locale(incoming_event)
        response = OutgoingEvent(social_details=incoming_event.social_details)
        message_1 = self._translator.get_translation_instance(user_locale).with_text("start_text_1").translate()
        message_2 = self._translator.get_translation_instance(user_locale).with_text("start_text_2").translate()
        message_3 = self._get_help_and_info_message(user_locale)
        button_text = self._translator.get_translation_instance(user_locale).with_text("start_button").translate()
        response.with_message(TextualResponse(message_1))
        response.with_message(TextualResponse(message_2))
        final_message_with_button = RapidAnswerResponse(TextualResponse(message_3))
        final_message_with_button.with_textual_option(button_text, self.INTENT_QUESTION)
        response.with_message(final_message_with_button)
        return response

    def _get_command_list(self) -> str:
        return self._translator.get_translation_instance('en').with_text("info_text").translate()

    def handle_wenet_textual_message(self, message: TextualMessage) -> NotificationEvent:
        pass

    def handle_wenet_notification_message(self, message: TaskNotification) -> NotificationEvent:
        pass

    def handle_wenet_authentication_result(self, message: WeNetAuthentication) -> NotificationEvent:
        # get and put wenet user id into context here
        pass
