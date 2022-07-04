from __future__ import absolute_import, annotations

import datetime
import logging
from typing import Optional, List, Dict, Set

from wenet.interface.client import Oauth2Client
from wenet.interface.service_api import ServiceApiInterface
from wenet.storage.cache import BaseCache

from ask_for_help_bot.pending_conversations import PendingQuestionToAnswer, PendingWenetMessage
from chatbot_core.model.user_context import UserConversationContext
from chatbot_core.v3.connector.social_connector import SocialConnector
from chatbot_core.v3.job.job import SocialJob
from chatbot_core.v3.logger.event_logger import LoggerConnector
from chatbot_core.v3.model.outgoing_event import NotificationEvent

from ask_for_help_bot.state_mixin import StateMixin
from common.authentication_event import CreationError
from common.messages_to_log import LogMessageHandler

logger = logging.getLogger("uhopper.chatbot.wenet.askforhelp.pending_messages_job")


class PendingMessagesJob(SocialJob, StateMixin):
    """
    This job passes all the contexts, checking whether they contain pending questions or wenet messages dictionaries.
    In case they do and the user is not in any state, and for the question ones also the right amount of time since
    the question was added is passed, the stored messages are sent to the user,
    and the pending questions or wenet messages are removed from the dictionaries.
    """
    REMINDER_MINUTES = 60
    CONTEXT_WENET_USER_ID = "wenet_user_id"

    def __init__(self, job_id, instance_namespace: str, connector: SocialConnector,
                 logger_connectors: Optional[List[LoggerConnector]], app_id: str, client_secret: str,
                 oauth_cache: BaseCache, wenet_authentication_management_url: str, wenet_instance_url: str) -> None:
        super().__init__(job_id, instance_namespace, connector, logger_connectors)
        self.app_id = app_id
        self.client_secret = client_secret
        self.oauth_cache = oauth_cache
        self.wenet_authentication_management_url = wenet_authentication_management_url
        self.wenet_instance_url = wenet_instance_url
        self.message_parser_for_logs = LogMessageHandler(self.app_id, "Telegram")

    def _should_run(self) -> bool:
        return True

    def execute(self, **kwargs) -> None:
        contexts = self._interface_connector.get_user_contexts(self._instance_namespace, None)
        for context in contexts:
            if not self._is_doing_another_action(context.context):
                try:
                    self._handle_delayed_wenet_messages(context)
                except Exception as e:
                    logger.exception(f"An exception [{type(e)}] occurs handling the context [{context}] for sending delayed wenet messages", exc_info=e)

            if not self._is_doing_another_action(context.context):
                try:
                    self._handle_remind_me_later_messages(context)
                except Exception as e:
                    logger.exception(f"An exception [{type(e)}] occurs handling the context [{context}] for sending remind me later messages", exc_info=e)

    def _handle_delayed_wenet_messages(self, context: UserConversationContext) -> None:
        """
        Check whether a context contains some pending wenet messages. In case they do, they are handled sending the
        pending wenet messages and removing the wenet messages from the dict.
        """
        notifications: List[NotificationEvent] = []
        responses_to: List[Optional[str]] = []
        pending_wenet_messages: Dict[str, dict] = context.context.get_static_state(self.CONTEXT_PENDING_WENET_MESSAGES, dict())
        pending_wenet_messages_to_remove: Set[str] = set()
        is_context_modified: bool = False
        for pending_wenet_message_id in pending_wenet_messages:
            try:
                pending_wenet_message = PendingWenetMessage.from_repr(pending_wenet_messages[pending_wenet_message_id])
            except Exception as e:
                logger.exception(f"An exception [{type(e)}] occurs handling in parsing the pending wenet message [{pending_wenet_messages[pending_wenet_message_id]}]", exc_info=e)
                pending_wenet_messages_to_remove.add(pending_wenet_message_id)
                is_context_modified = True
                continue

            notifications.append(NotificationEvent(social_details=pending_wenet_message.social_details, messages=pending_wenet_message.responses))
            responses_to.append(pending_wenet_message.response_to)
            pending_wenet_messages_to_remove.add(pending_wenet_message.pending_wenet_message_id)
            is_context_modified = True

        if not self._is_doing_another_action(context.context):
            for i, notification in enumerate(notifications):
                notification.with_context(context.context)
                oauth_client = Oauth2Client(self.app_id, self.client_secret, notification.social_details.unique_id(), self.oauth_cache, token_endpoint_url=self.wenet_authentication_management_url)
                service_api = ServiceApiInterface(oauth_client, self.wenet_instance_url)
                try:
                    self.send_notification(notification)
                    logger.debug(f"Sent delayed messages with the notification: [{notification.to_repr()}]")

                    if responses_to[i]:
                        for outgoing_message in notification.messages:
                            try:
                                service_api.log_message(self.message_parser_for_logs.create_response(outgoing_message, context.context.get_static_state(self.CONTEXT_WENET_USER_ID), responses_to[i]))
                            except TypeError as e:
                                logger.warning("Unsupported message to log", exc_info=e)
                            except CreationError:
                                logger.warning("Unable to send logs to the service API")
                except Exception as e:
                    logger.exception(f"An exception [{type(e)}] occurs sending the notification [{notification.to_repr()}]", exc_info=e)

            for pending_wenet_message_id in pending_wenet_messages_to_remove:
                pending_wenet_messages.pop(pending_wenet_message_id)

            if is_context_modified:
                context.context.with_static_state(self.CONTEXT_PENDING_WENET_MESSAGES, pending_wenet_messages)
                self._interface_connector.update_user_context(context)

    def _handle_remind_me_later_messages(self, context: UserConversationContext) -> None:
        """
        Check whether a context contains some pending questions to be answered. In case they do, they are handled
        sending the pending questions if the right amount of time since the question was added is passed
        and removing the questions from the dict.
        """
        notifications: List[NotificationEvent] = []
        responses_to: List[Optional[str]] = []
        pending_answers: Dict[str, dict] = context.context.get_static_state(self.CONTEXT_PENDING_ANSWERS, dict())
        questions_to_remove: Set[str] = set()
        is_context_modified: bool = False
        for question_id in pending_answers:
            try:
                pending_answer = PendingQuestionToAnswer.from_repr(pending_answers[question_id])
            except Exception as e:
                logger.exception(f"An exception [{type(e)}] occurs handling in parsing the pending answer [{pending_answers[question_id]}]", exc_info=e)
                questions_to_remove.add(question_id)
                is_context_modified = True
                continue

            if pending_answer.sent is not None and pending_answer.sent + datetime.timedelta(minutes=self.REMINDER_MINUTES) <= datetime.datetime.now():
                notifications.append(NotificationEvent(social_details=pending_answer.social_details, messages=[pending_answer.response]))
                responses_to.append(pending_answer.response_to)
                questions_to_remove.add(pending_answer.question_id)
                is_context_modified = True

        if not self._is_doing_another_action(context.context):
            for i, notification in enumerate(notifications):
                notification.with_context(context.context)
                oauth_client = Oauth2Client(self.app_id, self.client_secret, notification.social_details.unique_id(), self.oauth_cache, token_endpoint_url=self.wenet_authentication_management_url)
                service_api = ServiceApiInterface(oauth_client, self.wenet_instance_url)
                try:
                    self.send_notification(notification)
                    logger.debug(f"Sent remind me later messages with the notification: [{notification.to_repr()}]")

                    if responses_to[i]:
                        for outgoing_message in notification.messages:
                            try:
                                service_api.log_message(self.message_parser_for_logs.create_response(outgoing_message, context.context.get_static_state(self.CONTEXT_WENET_USER_ID), responses_to[i]))
                            except TypeError as e:
                                logger.warning("Unsupported message to log", exc_info=e)
                            except CreationError:
                                logger.warning("Unable to send logs to the service API")

                except Exception as e:
                    logger.exception(f"An exception [{type(e)}] occurs sending the notification [{notification.to_repr()}]", exc_info=e)

            for question_id in questions_to_remove:
                pending_answers.pop(question_id)

            if is_context_modified:
                context.context.with_static_state(self.CONTEXT_PENDING_ANSWERS, pending_answers)
                self._interface_connector.update_user_context(context)
