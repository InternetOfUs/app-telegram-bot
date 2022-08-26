from __future__ import absolute_import, annotations

import json
import logging
import os
import random
import uuid
from datetime import datetime, timedelta
from json import JSONDecodeError
from typing import Optional, List

import requests
from chatbot_core.model.user_context import UserConversationContext
from emoji import emojize, demojize
from wenet.interface.service_api import ServiceApiInterface

from ask_for_help_bot.pending_conversations import PendingQuestionToAnswer, PendingWenetMessage
from ask_for_help_bot.pending_messages_job import PendingMessagesJob
from chatbot_core.model.context import ConversationContext
from chatbot_core.model.details import TelegramDetails, SocialDetails
from chatbot_core.model.event import IncomingSocialEvent
from chatbot_core.model.message import IncomingTextMessage
from chatbot_core.nlp.handler import NLPHandler
from chatbot_core.translator.translator import Translator
from chatbot_core.v3.connector.social_connector import SocialConnector
from chatbot_core.v3.connector.social_connectors.telegram_connector import TelegramSocialConnector
from chatbot_core.v3.handler.helpers.intent_manager import IntentFulfillerV3
from chatbot_core.v3.job.job_manager import JobManager
from chatbot_core.v3.logger.event_logger import LoggerConnector
from chatbot_core.v3.model.messages import TextualResponse, TelegramRapidAnswerResponse, \
    UrlImageResponse, ResponseMessage, TelegramTextualResponse
from chatbot_core.v3.model.outgoing_event import OutgoingEvent, NotificationEvent

from ask_for_help_bot.state_mixin import StateMixin
from common.button_payload import ButtonPayload
from common.wenet_event_handler import WenetEventHandler
from uhopper.utils.alert.module import AlertModule
from common.authentication_event import CreationError
from wenet.interface.exceptions import RefreshTokenExpiredError
from common.authentication_event import WeNetAuthenticationEvent
from wenet.model.callback_message.message import Message
from common.callback_messages import QuestionExpirationMessage, TextualMessage, QuestionToAnswerMessage, \
    AnsweredQuestionMessage, IncentiveMessage, IncentiveBadge, AnsweredPickedMessage
from wenet.model.task.task import Task, TaskGoal
from wenet.model.task.transaction import TaskTransaction
from wenet.model.user.profile import WeNetUserProfile


logger = logging.getLogger("uhopper.chatbot.wenet.askforhelp.chatbot")


class AskForHelpHandler(WenetEventHandler, StateMixin):
    """
    The class that manages the Ask For Help WeNet chatbot.

    This is a DFA (deterministic finite automata), where the next action is given either by the current state,
    the intent of the incoming event or both the two things.
    """
    # context keys
    CONTEXT_ASKED_QUESTION = "asked_question"
    CONTEXT_QUESTION_DOMAIN = "question_domain"
    CONTEXT_DOMAIN_INTEREST = "domain_interest"
    CONTEXT_BELIEF_VALUES_SIMILARITY = "belief_values_similarity"
    CONTEXT_ANONYMOUS_QUESTION = "anonymous_question"
    CONTEXT_SOCIAL_CLOSENESS = "social_closeness"
    CONTEXT_ANONYMOUS_ANSWER = "anonymous_answer"
    CONTEXT_ANSWER_TO_QUESTION = "answer_to_question"
    CONTEXT_QUESTION_TO_ANSWER = "question_to_answer"
    CONTEXT_TASK_ID = "task_id"
    CONTEXT_TRANSACTION_ID = "transaction_id"
    CONTEXT_CHOSEN_ANSWER_REASON = "chosen_answer_reason"
    CONTEXT_QUESTIONER_NAME = "questioner_name"
    CONTEXT_QUESTION = "question"
    CONTEXT_BEST_ANSWER = "best_answer"
    CONTEXT_ANSWERER_NAME = "answerer_name"
    CONTEXT_ANSWERER_USER_ID = "answerer_user_id"
    CONTEXT_ANSWER_RECEIVED = "answer_received"
    CONTEXT_QUESTIONER_USER_ID = "questioner_user_id"
    CONTEXT_QUESTION_ANSWERED = "question_answered"
    CONTEXT_BLOCKED_USERS_FOR_CONTACT_REQUEST = "blocked_user_for_contact_request"
    # all the recognized intents
    INTENT_ASK = "/ask"
    INTENT_FIRST_QUESTION = "first_question"
    INTENT_ACADEMIC_SKILLS = "academic_skills"  # TODO update app logic and translations
    INTENT_BASIC_NEEDS = "basic_needs"
    INTENT_PHYSICAL_ACTIVITY = "physical_activity"
    INTENT_APPRECIATING_CULTURE = "appreciating_culture"
    INTENT_RANDOM_THOUGHTS = "random_thoughts"
    INTENT_PRODUCING_CULTURE = "producing_culture"
    INTENT_LEISURE_ACTIVITIES = "leisure_activities"
    INTENT_CAMPUS_LIFE = "campus_life"
    INTENT_SENSITIVE_QUESTION = "sensitive"
    INTENT_ANONYMOUS_QUESTION = "anonymous"
    INTENT_NOT_ANONYMOUS_QUESTION = "not_anonymous"
    INTENT_SIMILAR_DOMAIN = "similar"
    INTENT_INDIFFERENT_DOMAIN = "indifferent"
    INTENT_DIFFERENT_DOMAIN = "different"
    INTENT_SIMILAR_BELIEF_VALUES = "similar"
    INTENT_INDIFFERENT_BELIEF_VALUES = "indifferent"
    INTENT_DIFFERENT_BELIEF_VALUES = "different"
    INTENT_SIMILAR_SOCIALLY = "similar"
    INTENT_INDIFFERENT_SOCIALLY = "indifferent"
    INTENT_DIFFERENT_SOCIALLY = "different"
    INTENT_ASK_TO_NEARBY = "nearby"
    INTENT_ASK_TO_ANYWHERE = "anywhere"
    INTENT_ANSWER_ANONYMOUSLY = "answer_anonymously"
    INTENT_ANSWER_NOT_ANONYMOUSLY = "answer_not_anonymously"
    INTENT_ANSWER_QUESTION = "answer_question"
    INTENT_ANSWER_REMIND_LATER = "answer_remind_later"
    INTENT_ANSWER_NOT = "answer_not"
    INTENT_QUESTION_REPORT = "question_report"
    INTENT_REPORT_ABUSIVE = "abusive"
    INTENT_REPORT_SPAM = "spam"
    INTENT_ASK_MORE_ANSWERS = "ask_more_answers"
    INTENT_ANSWER_REPORT = "answer_report"
    INTENT_QUESTIONS = "/questions"
    INTENT_ANSWER_PICKED_QUESTION = "picked_answer"
    INTENT_LIKE_ANSWER = "like_answer"
    INTENT_BEST_ANSWER = "best_answer"
    INTENT_FOLLOW_UP = "follow_up"
    INTENT_SHARE_DETAILS = "share_details"
    INTENT_NOT_SHARE_DETAILS = "not_share_details"
    INTENT_NOT_NOW_SHARE_DETAILS = "not_now_share_details"
    INTENT_BLOCK_SHARE_DETAILS = "block_share_details"
    INTENT_SHARE_DETAILS_TO_QUESTIONER = "share_details_to_questioner"
    INTENT_PUBLISH = "publish"
    INTENT_NOT_PUBLISH = "not_publish"
    INTENT_AGREE_PUBLISH_ANONYMOUSLY = "agree_publish_anonymously"
    INTENT_AGREE_PUBLISH_NAME = "agree_publish_name"
    INTENT_NOT_AGREE_PUBLISH = "not_agree_publish"
    INTENT_NOT_AT_ALL_HELPFUL = "notAtAllHelpful"
    INTENT_SLIGHTLY_HELPFUL = "slightlyHelpful"
    INTENT_SOMEWHAT_HELPFUL = "somewhatHelpful"
    INTENT_VERY_HELPFUL = "veryHelpful"
    INTENT_EXTREMELY_HELPFUL = "extremelyHelpful"
    INTENT_CHOSEN_ANSWER_FUNNY = "funny"
    INTENT_CHOSEN_ANSWER_THOUGHTFUL = "thoughtful"
    INTENT_CHOSEN_ANSWER_INFORMATIVE = "informative"
    INTENT_CHOSEN_ANSWER_CREATIVE = "creative"
    INTENT_CHOSEN_ANSWER_HONEST = "honest"
    INTENT_CHOSEN_ANSWER_KIND = "kind"
    INTENT_CHOSEN_ANSWER_PERSONAL = "personal"
    INTENT_BADGES = "/badges"
    # INTENT_PROFILE = "/profile"
    # transaction labels
    LABEL_ANSWER_TRANSACTION = "answerTransaction"
    LABEL_NOT_ANSWER_TRANSACTION = "notAnswerTransaction"
    LABEL_REPORT_QUESTION_TRANSACTION = "reportQuestionTransaction"
    LABEL_REPORT_ANSWER_TRANSACTION = "reportAnswerTransaction"
    LABEL_MORE_ANSWER_TRANSACTION = "moreAnswerTransaction"
    LABEL_LIKE_ANSWER_TRANSACTION = "likeAnswerTransaction"
    LABEL_FOLLOW_UP_TRANSACTION = "followUpTransaction"
    LABEL_BEST_ANSWER_TRANSACTION = "bestAnswerTransaction"
    # keys used in Redis cache
    CACHE_LOCALE = "locale-{}"
    FIRST_ANSWER = "first-answer-{}"

    def __init__(self, instance_namespace: str, bot_id: str, handler_id: str, telegram_id: str, wenet_instance_url: str,
                 wenet_hub_url: str, app_id: str, client_secret: str, redirect_url: str, wenet_authentication_url: str,
                 wenet_authentication_management_url: str, task_type_id: str, community_id: str, max_users: int,
                 max_answers: int, expiration_duration: int, nearby_expiration_duration: int, survey_url: str, helper_url: Optional[str],
                 channel_id: Optional[str], publication_language: str, alert_module: AlertModule,
                 connector: SocialConnector, nlp_handler: Optional[NLPHandler], translator: Optional[Translator],
                 delay_between_messages_sec: Optional[int] = None, delay_between_text_sec: Optional[float] = None,
                 logger_connectors: Optional[List[LoggerConnector]] = None) -> None:
        super().__init__(instance_namespace, bot_id, handler_id, telegram_id, wenet_instance_url, wenet_hub_url, app_id,
                         client_secret, redirect_url, wenet_authentication_url, wenet_authentication_management_url,
                         task_type_id, community_id, alert_module, connector, nlp_handler, translator,
                         delay_between_messages_sec, delay_between_text_sec, logger_connectors)

        self.max_users = max_users
        self.max_answers = max_answers
        self.expiration_duration = expiration_duration
        self.neaby_expiration_duration = nearby_expiration_duration
        self.survey_url = survey_url
        self.helper_url = helper_url
        self.channel_id = channel_id
        self.publication_language = publication_language

        JobManager.instance().add_job(PendingMessagesJob("wenet_ask_for_help_pending_messages_job", self._instance_namespace, self._connector, logger_connectors, self.app_id, self.client_secret, self.oauth_cache, self.wenet_authentication_management_url, self.wenet_instance_url))
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3(self.INTENT_ASK, self.action_question_0).with_rule(
                intent=self.INTENT_ASK
            )
        )
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3(self.INTENT_FIRST_QUESTION, self.action_question_0).with_rule(
                intent=self.INTENT_FIRST_QUESTION
            )
        )
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3("", self.action_question_1).with_rule(
                static_context=(self.CONTEXT_CURRENT_STATE, self.STATE_QUESTION_0)
            )
        )
        domain_intents = [self.INTENT_ACADEMIC_SKILLS, self.INTENT_BASIC_NEEDS, self.INTENT_PHYSICAL_ACTIVITY,
                          self.INTENT_APPRECIATING_CULTURE, self.INTENT_RANDOM_THOUGHTS, self.INTENT_PRODUCING_CULTURE,
                          self.INTENT_LEISURE_ACTIVITIES, self.INTENT_CAMPUS_LIFE, self.INTENT_SENSITIVE_QUESTION]
        for domain_intent in domain_intents:
            self.intent_manager.with_fulfiller(
                IntentFulfillerV3(domain_intent, self.action_question_2).with_rule(
                    intent=domain_intent,
                    static_context=(self.CONTEXT_CURRENT_STATE, self.STATE_QUESTION_1)
                )
            )
        anonymous_intents = [self.INTENT_ANONYMOUS_QUESTION, self.INTENT_NOT_ANONYMOUS_QUESTION]
        for anonymous_intent in anonymous_intents:
            self.intent_manager.with_fulfiller(
                IntentFulfillerV3(anonymous_intent, self.action_question_3).with_rule(
                    intent=anonymous_intent,
                    static_context=(self.CONTEXT_CURRENT_STATE, self.STATE_QUESTION_2)
                )
            )

        domain_similarity_intents = [self.INTENT_SIMILAR_DOMAIN, self.INTENT_DIFFERENT_DOMAIN,
                                     self.INTENT_INDIFFERENT_DOMAIN]
        for domain_similarity_intent in domain_similarity_intents:
            self.intent_manager.with_fulfiller(
                IntentFulfillerV3(domain_similarity_intent, self.action_question_4).with_rule(
                    intent=domain_similarity_intent,
                    static_context=(self.CONTEXT_CURRENT_STATE, self.STATE_QUESTION_3)
                )
            )
        belief_values_similarity_intents = [self.INTENT_SIMILAR_BELIEF_VALUES, self.INTENT_DIFFERENT_BELIEF_VALUES,
                                            self.INTENT_INDIFFERENT_BELIEF_VALUES]
        for belief_values_similarity_intent in belief_values_similarity_intents:
            self.intent_manager.with_fulfiller(
                IntentFulfillerV3(belief_values_similarity_intent, self.action_question_5).with_rule(
                    intent=belief_values_similarity_intent,
                    static_context=(self.CONTEXT_CURRENT_STATE, self.STATE_QUESTION_4)
                )
            )
        social_similarity_intents = [self.INTENT_SIMILAR_SOCIALLY, self.INTENT_DIFFERENT_SOCIALLY,
                                     self.INTENT_INDIFFERENT_SOCIALLY]
        for social_similarity_intent in social_similarity_intents:
            self.intent_manager.with_fulfiller(
                IntentFulfillerV3(social_similarity_intent, self.action_question_6).with_rule(
                    intent=social_similarity_intent,
                    static_context=(self.CONTEXT_CURRENT_STATE, self.STATE_QUESTION_5)
                )
            )
        position_of_answer_intents = [self.INTENT_ASK_TO_NEARBY, self.INTENT_ASK_TO_ANYWHERE]
        for position_of_answer_intent in position_of_answer_intents:
            self.intent_manager.with_fulfiller(
                IntentFulfillerV3(position_of_answer_intent, self.action_question_final).with_rule(
                    intent=position_of_answer_intent,
                    static_context=(self.CONTEXT_CURRENT_STATE, self.STATE_QUESTION_6)
                )
            )
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3("", self.action_answer_sensitive_question).with_rule(
                static_context=(self.CONTEXT_CURRENT_STATE, self.STATE_ANSWERING_SENSITIVE)
            )
        )
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3("", self.action_answer_question_2).with_rule(
                static_context=(self.CONTEXT_CURRENT_STATE, self.STATE_ANSWERING)
            )
        )
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3(self.INTENT_ANSWER_ANONYMOUSLY, self.action_answer_question_anonymously).with_rule(
                intent=self.INTENT_ANSWER_ANONYMOUSLY,
                static_context=(self.CONTEXT_CURRENT_STATE, self.STATE_ANSWERING_ANONYMOUSLY)
            )
        )
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3(self.INTENT_ANSWER_NOT_ANONYMOUSLY, self.action_answer_question_anonymously).with_rule(
                intent=self.INTENT_ANSWER_NOT_ANONYMOUSLY,
                static_context=(self.CONTEXT_CURRENT_STATE, self.STATE_ANSWERING_ANONYMOUSLY)
            )
        )
        publish_intents = [self.INTENT_AGREE_PUBLISH_ANONYMOUSLY, self.INTENT_AGREE_PUBLISH_NAME, self.INTENT_NOT_AGREE_PUBLISH]
        for publishing_intent in publish_intents:
            self.intent_manager.with_fulfiller(
                IntentFulfillerV3(publishing_intent, self.action_agree_to_publish).with_rule(
                    intent=publishing_intent,
                    static_context=(self.CONTEXT_CURRENT_STATE, self.STATE_PUBLISHING_ANSWER_TO_CHANNEL)
                )
            )
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3(self.INTENT_QUESTIONS, self.action_answer).with_rule(
                intent=self.INTENT_QUESTIONS
            )
        )
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3(self.INTENT_NOT_SHARE_DETAILS, self.action_follow_up_1).with_rule(
                intent=self.INTENT_NOT_SHARE_DETAILS,
                static_context=(self.CONTEXT_CURRENT_STATE, self.STATE_FOLLOW_UP_0)
            )
        )
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3(self.INTENT_SHARE_DETAILS, self.action_follow_up_1).with_rule(
                intent=self.INTENT_SHARE_DETAILS,
                static_context=(self.CONTEXT_CURRENT_STATE, self.STATE_FOLLOW_UP_0)
            )
        )
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3(self.INTENT_NOT_PUBLISH, self.action_best_answer_publish).with_rule(
                intent=self.INTENT_NOT_PUBLISH,
                static_context=(self.CONTEXT_CURRENT_STATE, self.STATE_BEST_ANSWER_PUBLISH)
            )
        )
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3(self.INTENT_PUBLISH, self.action_best_answer_publish).with_rule(
                intent=self.INTENT_PUBLISH,
                static_context=(self.CONTEXT_CURRENT_STATE, self.STATE_BEST_ANSWER_PUBLISH)
            )
        )
        why_choose_answer_intents = [self.INTENT_CHOSEN_ANSWER_FUNNY, self.INTENT_CHOSEN_ANSWER_THOUGHTFUL, self.INTENT_CHOSEN_ANSWER_INFORMATIVE,
                                     self.INTENT_CHOSEN_ANSWER_KIND, self.INTENT_CHOSEN_ANSWER_CREATIVE, self.INTENT_CHOSEN_ANSWER_HONEST,
                                     self.INTENT_CHOSEN_ANSWER_PERSONAL]
        for why_choose_answer_intent in why_choose_answer_intents:
            self.intent_manager.with_fulfiller(
                IntentFulfillerV3(why_choose_answer_intent, self.action_best_answer_1).with_rule(
                    intent=why_choose_answer_intent,
                    static_context=(self.CONTEXT_CURRENT_STATE, self.STATE_BEST_ANSWER_0)
                )
            )
        answer_rating_intents = [self.INTENT_NOT_AT_ALL_HELPFUL, self.INTENT_SLIGHTLY_HELPFUL,
                                 self.INTENT_SOMEWHAT_HELPFUL, self.INTENT_VERY_HELPFUL, self.INTENT_EXTREMELY_HELPFUL]
        for answer_rating_intent in answer_rating_intents:
            self.intent_manager.with_fulfiller(
                IntentFulfillerV3(answer_rating_intent, self.action_best_answer_2).with_rule(
                    intent=answer_rating_intent,
                    static_context=(self.CONTEXT_CURRENT_STATE, self.STATE_BEST_ANSWER_1)
                )
            )
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3(self.INTENT_BADGES, self.action_badges).with_rule(
                intent=self.INTENT_BADGES
            )
        )
        # self.intent_manager.with_fulfiller(
        #     IntentFulfillerV3(self.INTENT_PROFILE, self.action_profile).with_rule(
        #         intent=self.INTENT_PROFILE
        #     )
        # )
        # keep this as the last one!
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3("", self.handle_button_with_payload).with_rule(
                regex=self.INTENT_BUTTON_WITH_PAYLOAD.format("[A-Za-z0-9-]+"))
        )

    def _get_user_locale_from_wenet_id(self, wenet_user_id: str, context: Optional[ConversationContext] = None) -> str:
        if not context:
            user_accounts = self.get_user_accounts(wenet_user_id)
            if len(user_accounts) != 1:
                logger.error(f"No context associated with WeNet user {wenet_user_id}")
                raise Exception(f"No context associated with WeNet user {wenet_user_id}")
            context = user_accounts[0].context
        cached_locale = self.cache.get(self.CACHE_LOCALE.format(wenet_user_id))
        if not cached_locale:
            service_api = self._get_service_api_interface_connector_from_context(context)
            user_object = service_api.get_user_profile(wenet_user_id)
            if not user_object:
                logger.info(f"Unable to retrieve user profile [{wenet_user_id}]")
                return "en"
            locale = user_object.locale if user_object.locale else "en"
            self.cache.cache({"locale": locale}, ttl=int(os.getenv("LOCALE_TTL", 86400)), key=self.CACHE_LOCALE.format(wenet_user_id))
            return locale
        return cached_locale.get("locale", "en")

    def _get_user_locale_from_incoming_event(self, incoming_event: IncomingSocialEvent) -> str:
        wenet_user_id = incoming_event.context.get_static_state(self.CONTEXT_WENET_USER_ID, None)
        if not wenet_user_id:
            logger.info("Impossible to get user locale from incoming event. The Wenet user ID is not in the context")
            return "en"
        return self._get_user_locale_from_wenet_id(wenet_user_id, context=incoming_event.context)

    def _get_help_and_info_message(self, locale: str) -> str:
        return self._translator.get_translation_instance(locale).with_text("info_text").translate()

    def action_info(self, incoming_event: IncomingSocialEvent, intent: str) -> OutgoingEvent:
        user_locale = self._get_user_locale_from_incoming_event(incoming_event)
        response = OutgoingEvent(social_details=incoming_event.social_details)
        response.with_message(TextualResponse(self._get_help_and_info_message(user_locale)))
        return response

    def action_error(self, incoming_event: IncomingSocialEvent, intent: str) -> OutgoingEvent:
        user_locale = self._get_user_locale_from_incoming_event(incoming_event)
        response = OutgoingEvent(social_details=incoming_event.social_details)
        message = self._translator.get_translation_instance(user_locale).with_text("error_text").translate()
        response.with_message(TextualResponse(message))
        return response

    def _clear_context(self, context: ConversationContext) -> ConversationContext:
        context_to_remove = [
            self.CONTEXT_CURRENT_STATE, self.CONTEXT_ASKED_QUESTION, self.CONTEXT_QUESTION_DOMAIN,
            self.CONTEXT_ANONYMOUS_QUESTION, self.CONTEXT_DOMAIN_INTEREST, self.CONTEXT_BELIEF_VALUES_SIMILARITY,
            self.CONTEXT_SOCIAL_CLOSENESS, self.CONTEXT_ANSWER_TO_QUESTION, self.CONTEXT_QUESTION_TO_ANSWER,
            self.CONTEXT_TASK_ID, self.CONTEXT_TRANSACTION_ID, self.CONTEXT_CHOSEN_ANSWER_REASON,
            self.CONTEXT_QUESTIONER_NAME, self.CONTEXT_QUESTION, self.CONTEXT_BEST_ANSWER, self.CONTEXT_ANSWERER_NAME,
            self.CONTEXT_ANSWERER_USER_ID, self.CONTEXT_ANSWER_RECEIVED, self.CONTEXT_QUESTIONER_USER_ID,
            self.CONTEXT_QUESTION_ANSWERED, self.CONTEXT_ANONYMOUS_ANSWER
        ]
        for context_key in context_to_remove:
            context.delete_static_state(context_key)
        return context

    def cancel_action(self, incoming_event: IncomingSocialEvent, intent: str) -> OutgoingEvent:
        context = incoming_event.context
        self._clear_context(context)
        user_locale = self._get_user_locale_from_incoming_event(incoming_event)
        message = self._translator.get_translation_instance(user_locale).with_text("cancel_text").translate()
        response = OutgoingEvent(social_details=incoming_event.social_details)
        response.with_message(TextualResponse(message))
        response.with_context(context)
        return response

    def handle_help(self, message: IncomingSocialEvent, intent: str) -> OutgoingEvent:
        user_locale = self._get_user_locale_from_incoming_event(message)
        response = OutgoingEvent(social_details=message.social_details)
        response.with_message(TextualResponse(self._get_help_and_info_message(user_locale)))
        return response

    def _get_start_messages(self, user_locale: str) -> List[ResponseMessage]:
        message_1 = self._translator.get_translation_instance(user_locale).with_text("start_text_1").translate()
        message_2 = self._translator.get_translation_instance(user_locale).with_text("start_text_2").translate()
        survey_message = self._translator.get_translation_instance(user_locale).with_text("survey_promo") \
            .with_substitution("survey_url", self.survey_url) \
            .translate()
        badges_message = self._translator.get_translation_instance(user_locale).with_text("badges_promo")\
            .with_substitution("base_url", self.wenet_hub_url)\
            .with_substitution("app_id", self.app_id)\
            .translate()
        info_message = self._get_help_and_info_message(user_locale)
        if self.helper_url:
            conduct_message = self._translator.get_translation_instance(user_locale).with_text("question_0_with_helper_url") \
                .with_substitution("helper_url", self.helper_url) \
                .translate()
        else:
            conduct_message = self._translator.get_translation_instance(user_locale).with_text("question_0").translate()
        button_text = self._translator.get_translation_instance(user_locale).with_text("start_button").translate()
        conduct_message_with_button = TelegramRapidAnswerResponse(TextualResponse(conduct_message))
        conduct_message_with_button.with_textual_option(button_text, self.INTENT_FIRST_QUESTION)
        return [
            TextualResponse(message_1),
            TextualResponse(message_2),
            TextualResponse(survey_message),
            TextualResponse(badges_message),
            TextualResponse(info_message),
            conduct_message_with_button
        ]

    def action_start(self, incoming_event: IncomingSocialEvent, intent: str) -> OutgoingEvent:
        user_locale = self._get_user_locale_from_incoming_event(incoming_event)
        response = OutgoingEvent(
            social_details=incoming_event.social_details,
            messages=self._get_start_messages(user_locale)
        )
        return response

    @staticmethod
    def _prepare_string_to_wenet(text: str) -> str:
        """
        demojize is used handle and encode emojies and them using emojize it is possible to reconstruct them
        json.dumps is used to handle and encode non-ascii characters and then using json.loads it is possible to reconstruct them
        """
        return json.dumps(demojize(text))

    @staticmethod
    def _prepare_string_to_telegram(raw_text: str) -> str:
        """
        json.loads is used to reconstruct non-ascii characters previously encoded using json.dumps
        emojize it used to reconstruct emojies previously encoded using demojize
        """
        try:
            decoded_text = json.loads(raw_text)
        except JSONDecodeError:
            decoded_text = raw_text

        return emojize(decoded_text, use_aliases=True)

    def _get_notification_event_based_on_what_user_is_doing(self, context: ConversationContext, social_details: SocialDetails, responses: List[ResponseMessage], response_to: str) -> NotificationEvent:
        if self._is_doing_another_action(context):
            pending_wenet_messages = context.get_static_state(self.CONTEXT_PENDING_WENET_MESSAGES, dict())
            pending_wenet_message_id = str(uuid.uuid4())
            pending_wenet_message = PendingWenetMessage(pending_wenet_message_id, responses, social_details, response_to=response_to)
            pending_wenet_messages[pending_wenet_message_id] = pending_wenet_message.to_repr()
            context.with_static_state(self.CONTEXT_PENDING_WENET_MESSAGES, pending_wenet_messages)
            return NotificationEvent(social_details, [], context)
        else:
            return NotificationEvent(social_details, responses, context)

    def handle_wenet_textual_message(self, message: TextualMessage, response_to: str) -> NotificationEvent:
        """
        Handle all the incoming textual messages
        """
        user_accounts = self.get_user_accounts(message.receiver_id)
        if len(user_accounts) != 1:
            logger.error(f"No context associated with WeNet user {message.receiver_id}")
            raise ValueError(f"No context associated with WeNet user {message.receiver_id}")

        user_account = user_accounts[0]
        context = user_account.context

        title = "" if message.title == "" else f"*{self.parse_text_with_markdown(message.title)}*\n"
        response = TelegramTextualResponse(f"{title}_{self.parse_text_with_markdown(message.text)}_")

        # in case the user was doing something else the received message is stored
        return self._get_notification_event_based_on_what_user_is_doing(context, user_account.social_details, [response], response_to)

    def _handle_question(self, message: QuestionToAnswerMessage, user_object: WeNetUserProfile, questioning_user: WeNetUserProfile) -> TelegramRapidAnswerResponse:  # TODO handle in a special way proximity questions?
        # Translate the message that someone in the community has a question and insert the details of the question, treat differently sensitive questions
        message_string = self._translator.get_translation_instance(user_object.locale)
        sensitive = message.attributes["domain"] == self.INTENT_SENSITIVE_QUESTION
        anonymous = message.attributes.get("anonymous", False)
        if sensitive:
            message_string = message_string.with_text("answer_sensitive_message_0")
        else:
            message_string = message_string.with_text("answer_message_0")

        message_string = message_string.with_substitution("question", self.parse_text_with_markdown(self._prepare_string_to_telegram(message.question))) \
            .with_substitution("user", questioning_user.name.first if questioning_user.name.first and not anonymous else self._translator.get_translation_instance(user_object.locale).with_text("anonymous_user").translate()) \
            .translate()

        # we create ids of all buttons, to know which buttons invalidate when one of them is clicked
        button_ids = [str(uuid.uuid4()) for _ in range(4)]
        button_data = {
            "task_id": message.task_id,
            "question": self._prepare_string_to_telegram(message.question),
            "sensitive": sensitive,
            "username": questioning_user.name.first if questioning_user.name.first and not anonymous else self._translator.get_translation_instance(user_object.locale).with_text("anonymous_user").translate(),
            "related_buttons": button_ids,
        }
        response = TelegramRapidAnswerResponse(TextualResponse(message_string), row_displacement=[2, 2])
        self.cache.cache(ButtonPayload(button_data, self.INTENT_ANSWER_QUESTION).to_repr(), key=button_ids[0])
        response.with_textual_option(self._translator.get_translation_instance(user_object.locale).with_text("answer_question_button").translate(), self.INTENT_BUTTON_WITH_PAYLOAD.format(button_ids[0]))
        self.cache.cache(ButtonPayload(button_data, self.INTENT_ANSWER_REMIND_LATER).to_repr(), key=button_ids[1])
        response.with_textual_option(self._translator.get_translation_instance(user_object.locale).with_text("answer_remind_later_button").translate(), self.INTENT_BUTTON_WITH_PAYLOAD.format(button_ids[1]))
        self.cache.cache(ButtonPayload(button_data, self.INTENT_ANSWER_NOT).to_repr(), key=button_ids[2])
        response.with_textual_option(self._translator.get_translation_instance(user_object.locale).with_text("answer_not_button").translate(), self.INTENT_BUTTON_WITH_PAYLOAD.format(button_ids[2]))
        self.cache.cache(ButtonPayload(button_data, self.INTENT_QUESTION_REPORT).to_repr(), key=button_ids[3])
        response.with_textual_option(self._translator.get_translation_instance(user_object.locale).with_text("answer_report_button").translate(), self.INTENT_BUTTON_WITH_PAYLOAD.format(button_ids[3]))
        return response

    def _handle_answered_question(self, message: AnsweredQuestionMessage, user_object: WeNetUserProfile, answerer_user: WeNetUserProfile) -> TelegramRapidAnswerResponse:
        answer_text = self.parse_text_with_markdown(self._prepare_string_to_telegram(message.answer))
        answerer_name = answerer_user.name.first if answerer_user.name.first and not message.attributes.get("anonymous", False) else self._translator.get_translation_instance(user_object.locale).with_text("anonymous_user").translate()
        question_text = self.parse_text_with_markdown(self._prepare_string_to_telegram(message.attributes["question"]))
        # Translate the message that there is a new answer and insert the details of the question and answer
        message_string = self._translator.get_translation_instance(user_object.locale) \
            .with_text("new_answer_message") \
            .with_substitution("question", question_text) \
            .with_substitution("answer", answer_text) \
            .with_substitution("username", answerer_name) \
            .translate()

        answer = TelegramRapidAnswerResponse(TextualResponse(message_string), row_displacement=[1, 1, 1])
        button_report_text = self._translator.get_translation_instance(user_object.locale).with_text("answer_report_button").translate()
        button_follow_up_text = self._translator.get_translation_instance(user_object.locale).with_text("follow_up_button").with_substitution("answerer", answerer_name).translate()
        button_like_answer_text = self._translator.get_translation_instance(user_object.locale).with_text("like_answer_button").translate()
        button_ids = [str(uuid.uuid4()) for _ in range(3)]
        button_data = {
            "answerer_user_id": answerer_user.profile_id,
            "answerer_name": answerer_name,
            "answer": answer_text,
            "transaction_id": message.transaction_id,
            "task_id": message.attributes["taskId"],
            "question": question_text,
            "questioner_user_id": user_object.profile_id,
            "related_buttons": [button_ids[0], button_ids[2]]  # We want to allow more clicks for this set of buttons: not all the buttons should expire when we press one of them, only like and report are mutually exclusive
        }
        self.cache.cache(ButtonPayload(button_data, self.INTENT_LIKE_ANSWER).to_repr(), key=button_ids[0])
        self.cache.cache(ButtonPayload(button_data, self.INTENT_ANSWER_REPORT).to_repr(), key=button_ids[2])
        button_data["related_buttons"] = [button_ids[1]]  # Follow up is independent of like and report
        self.cache.cache(ButtonPayload(button_data, self.INTENT_FOLLOW_UP).to_repr(), key=button_ids[1])
        answer.with_textual_option(button_like_answer_text, self.INTENT_BUTTON_WITH_PAYLOAD.format(button_ids[0]))
        answer.with_textual_option(button_follow_up_text, self.INTENT_BUTTON_WITH_PAYLOAD.format(button_ids[1]))
        answer.with_textual_option(button_report_text, self.INTENT_BUTTON_WITH_PAYLOAD.format(button_ids[2]))
        return answer

    def _handle_answered_picked(self, message: AnsweredPickedMessage, user_object: WeNetUserProfile) -> TextualResponse:
        # Translate the message that the answer to a question was picked as the best and insert the details of the question
        message_string = self._translator.get_translation_instance(user_object.locale) \
            .with_text("picked_best_answer") \
            .with_substitution("question", self.parse_text_with_markdown(self._prepare_string_to_telegram(message.attributes.get("question")))) \
            .translate()
        return TextualResponse(message_string)

    def _handle_question_expiration(self, message: QuestionExpirationMessage, service_api: ServiceApiInterface, user_object: WeNetUserProfile) -> List[TelegramRapidAnswerResponse]:
        locale = user_object.locale
        transaction_ids = []
        question_text = self.parse_text_with_markdown(self._prepare_string_to_telegram(message.question))
        message_answers = []
        message_users = []
        task = service_api.get_task(message.task_id)
        for i in message.attributes.get("listOfTransactionIds"):
            for transaction in task.transactions:
                if transaction.id == i and transaction.label == self.LABEL_ANSWER_TRANSACTION:
                    message_answers.append(self.parse_text_with_markdown(self._prepare_string_to_telegram(transaction.attributes["answer"])))
                    answerer_user = service_api.get_user_profile(transaction.actioneer_id)
                    message_users.append(answerer_user.name.first if answerer_user.name.first and not transaction.attributes.get("anonymous", False) else self._translator.get_translation_instance(locale).with_text("anonymous_user").translate())
                    transaction_ids.append(transaction.id)
                    break

        message_attributes = self._translator.get_translation_instance(locale) \
            .with_text("asked_message_without_attributes") \
            .with_substitution("user", question_text) \
            .with_substitution("question", question_text) \
            .translate()

        # TODO add selected attributes?

        message_upper_part = f"{message_attributes} \n\n"
        answer = []

        if len(message_answers) != 0:
            message_upper_part += f"{self._translator.get_translation_instance(locale).with_text('collected_answers').translate()} \n\n"
            answer_upper_part = TelegramRapidAnswerResponse(TextualResponse(message_upper_part))
            answer.append(answer_upper_part)

            message_string = ""

            n = 5  # group of answers to show on one batch of result
            output = []
            for i in range(len(message_answers)):
                answer_string = f"{i + 1}. {message_answers[i]} - {message_users[i]} \n"
                output.append(answer_string)
            grouped_answers = [output[i:i + n] for i in range(0, len(output), n)]

            for i in range(len(grouped_answers)):
                message_string_middle = ""
                if i != len(grouped_answers) - 1:
                    for j in range(len(grouped_answers[i])):
                        message_string_middle += grouped_answers[i][j]
                    answer_middle_part = TelegramRapidAnswerResponse(TextualResponse(message_string_middle))
                    answer.append(answer_middle_part)
                else:
                    for j in range(len(grouped_answers[i])):
                        message_string += grouped_answers[i][j]

            message_string += f"\n{self._translator.get_translation_instance(locale).with_text('from_multiple_response').translate()}"

            button_rows = []
            button_count = len(transaction_ids) + 1
            for i in range(int(button_count / 2)):
                button_count -= 2
                button_rows.append(2)
                if button_count == 1:
                    button_rows.append(1)

            answer_lower_part = TelegramRapidAnswerResponse(TextualResponse(message_string), row_displacement=button_rows)
            button_ids = [str(uuid.uuid4()) for _ in range(len(transaction_ids) + 1)]
            for i in range(len(transaction_ids)):
                self.cache.cache(ButtonPayload({"task_id": message.task_id, "transaction_id": transaction_ids[i], "related_buttons": button_ids}, self.INTENT_BEST_ANSWER).to_repr(), key=button_ids[i])
                answer_lower_part.with_textual_option(f"#{1 + i}", self.INTENT_BUTTON_WITH_PAYLOAD.format(button_ids[i]))

        else:
            no_reply_string = self._translator.get_translation_instance(locale) \
                .with_text("no_answer_text") \
                .with_substitution("expiration_duration", str(int(self.neaby_expiration_duration / 3600)) if task.attributes.get("positionOfAnswerer") == self.INTENT_ASK_TO_NEARBY else str(int(self.expiration_duration / 3600)))\
                .translate()
            message_upper_part += no_reply_string
            answer_lower_part = TelegramRapidAnswerResponse(TextualResponse(message_upper_part), row_displacement=[1])
            button_ids = [str(uuid.uuid4())]

        button_data = {
            "task_id": message.attributes["taskId"],
            "related_buttons": button_ids
        }
        self.cache.cache(ButtonPayload(button_data, self.INTENT_ASK_MORE_ANSWERS).to_repr(), key=button_ids[len(transaction_ids)])
        button_ask_more_text = self._translator.get_translation_instance(locale).with_text("more_answers_button").translate()
        answer_lower_part.with_textual_option(button_ask_more_text, self.INTENT_BUTTON_WITH_PAYLOAD.format(button_ids[len(transaction_ids)]))
        answer.append(answer_lower_part)

        return answer

    def _get_incentive_badge_translated_message(self, message: IncentiveBadge, user_object: WeNetUserProfile) -> TextualResponse:
        if message.badge_class == os.getenv("FIRST_QUESTION_BADGE_ID"):
            return TextualResponse(self._translator.get_translation_instance(user_object.locale).with_text("first_question_badge").translate())
        elif message.badge_class == os.getenv("CURIOUS_LEVEL_1_BADGE_ID"):
            return TextualResponse(self._translator.get_translation_instance(user_object.locale).with_text("curious_level_1_badge").translate())
        elif message.badge_class == os.getenv("CURIOUS_LEVEL_2_BADGE_ID"):
            return TextualResponse(self._translator.get_translation_instance(user_object.locale).with_text("curious_level_2_badge").translate())
        elif message.badge_class == os.getenv("FIRST_ANSWER_BADGE_ID"):
            return TextualResponse(self._translator.get_translation_instance(user_object.locale).with_text("first_answer_badge").translate())
        elif message.badge_class == os.getenv("HELPER_LEVEL_1_BADGE_ID"):
            return TextualResponse(self._translator.get_translation_instance(user_object.locale).with_text("helper_level_1_badge").translate())
        elif message.badge_class == os.getenv("HELPER_LEVEL_2_BADGE_ID"):
            return TextualResponse(self._translator.get_translation_instance(user_object.locale).with_text("helper_level_2_badge").translate())
        elif message.badge_class == os.getenv("FIRST_GOOD_ANSWER_BADGE_ID"):
            return TextualResponse(self._translator.get_translation_instance(user_object.locale).with_text("first_good_answer_badge").translate())
        elif message.badge_class == os.getenv("GOOD_ANSWERS_LEVEL_1_BADGE_ID"):
            return TextualResponse(self._translator.get_translation_instance(user_object.locale).with_text("good_answers_level_1_badge").translate())
        elif message.badge_class == os.getenv("GOOD_ANSWERS_LEVEL_2_BADGE_ID"):
            return TextualResponse(self._translator.get_translation_instance(user_object.locale).with_text("good_answers_level_2_badge").translate())
        elif message.badge_class == os.getenv("FIRST_LONG_ANSWER_BADGE_ID"):
            return TextualResponse(self._translator.get_translation_instance(user_object.locale).with_text("first_long_answer_badge").translate())
        elif message.badge_class == os.getenv("EXPLAINER_LEVEL_1_BADGE_ID"):
            return TextualResponse(self._translator.get_translation_instance(user_object.locale).with_text("explainer_level_1_badge").translate())
        elif message.badge_class == os.getenv("EXPLAINER_LEVEL_2_BADGE_ID"):
            return TextualResponse(self._translator.get_translation_instance(user_object.locale).with_text("explainer_level_2_badge").translate())
        else:
            return TextualResponse(message.message)

    def handle_wenet_message(self, message: Message, response_to: str) -> NotificationEvent:
        # new question to answer, or a new answer to a question
        # incentive messages or badges
        user_accounts = self.get_user_accounts(message.receiver_id)
        if len(user_accounts) != 1:
            logger.error(f"No context associated with WeNet user {message.receiver_id}")
            raise Exception(f"No context associated with WeNet user {message.receiver_id}")

        user_account = user_accounts[0]
        context = user_account.context

        service_api = self._get_service_api_interface_connector_from_context(context)
        try:
            user_object = service_api.get_user_profile(str(message.receiver_id))
            if isinstance(message, QuestionToAnswerMessage):
                questioning_user = service_api.get_user_profile(str(message.user_id))
                response = self._handle_question(message, user_object, questioning_user)
                responses = [response]
            elif isinstance(message, AnsweredQuestionMessage):
                # handle an answer to a question
                answerer_id = message.user_id
                answerer_user = service_api.get_user_profile(str(answerer_id))
                response = self._handle_answered_question(message, user_object, answerer_user)
                responses = [response]
            elif isinstance(message, QuestionExpirationMessage):
                responses = self._handle_question_expiration(message, service_api, user_object)
            elif isinstance(message, AnsweredPickedMessage):
                # handle an answer picked for a question
                response = self._handle_answered_picked(message, user_object)
                responses = [response]
            elif isinstance(message, IncentiveMessage):
                # handle an incentive message
                response = TextualResponse(message.content)
                responses = [response]
            elif isinstance(message, IncentiveBadge):
                # handle an incentive badge
                response = self._get_incentive_badge_translated_message(message, user_object)
                image = UrlImageResponse(message.image_url)
                responses = [response, image]
            else:
                logger.warning(f"Received unrecognized message of type {type(message)}: {message.to_repr()}")
                raise Exception(f"Received unrecognized message of type {type(message)}: {message.to_repr()}")
        except RefreshTokenExpiredError as e:
            logger.exception("Refresh token is not longer valid", exc_info=e)
            notification_event = NotificationEvent(social_details=user_account.social_details)
            notification_event.with_message(
                TelegramTextualResponse(
                    f"Sorry, the login credential are no longer valid, please login again in order to continue to use the bot:\n "
                    f"{self.wenet_authentication_url}/login?client_id={self.app_id}&external_id={user_account.social_details.get_user_id()}",
                    parse_mode=None
                )
            )
            return notification_event

        # in case the user was doing something else the received message is stored
        return self._get_notification_event_based_on_what_user_is_doing(context, user_account.social_details, responses, response_to)

    def handle_button_with_payload(self, incoming_event: IncomingSocialEvent, _: str) -> OutgoingEvent:
        """
        Handle a button with a payload saved into redis
        """
        button_id = incoming_event.incoming_message.intent.value.split("--")[-1]
        raw_button_payload = self.cache.get(button_id)
        if raw_button_payload is None:
            response = OutgoingEvent(social_details=incoming_event.social_details)
            user_locale = self._get_user_locale_from_incoming_event(incoming_event)
            response.with_message(TextualResponse(self._translator.get_translation_instance(user_locale).with_text("expired_button_message").translate()))
            return response

        button_payload = ButtonPayload.from_repr(raw_button_payload)
        if "related_buttons" in button_payload.payload:
            # removing the button and all the related buttons from the cache
            for button_to_remove in button_payload.payload["related_buttons"]:
                self.cache.remove(button_to_remove)
        else:
            # in case the button is not related with any other buttons, just remove it from the cache
            self.cache.remove(button_id)

        if button_payload.intent == self.INTENT_ASK_MORE_ANSWERS:
            return self.action_more_answers(incoming_event, button_payload)
        elif button_payload.intent == self.INTENT_QUESTION_REPORT or button_payload.intent == self.INTENT_ANSWER_REPORT:
            return self.action_report_message(incoming_event, button_payload)
        elif button_payload.intent == self.INTENT_REPORT_ABUSIVE or button_payload.intent == self.INTENT_REPORT_SPAM:
            return self.action_report_message_1(incoming_event, button_payload)
        elif button_payload.intent == self.INTENT_FOLLOW_UP:
            return self.action_follow_up_0(incoming_event, button_payload)
        elif button_payload.intent == self.INTENT_SHARE_DETAILS_TO_QUESTIONER:
            return self.action_follow_up_2(incoming_event, button_payload)
        elif button_payload.intent == self.INTENT_NOT_NOW_SHARE_DETAILS:
            return self.action_not_follow_up(incoming_event, button_payload)
        elif button_payload.intent == self.INTENT_BLOCK_SHARE_DETAILS:
            return self.action_block_follow_up(incoming_event, button_payload)
        elif button_payload.intent == self.INTENT_LIKE_ANSWER:
            return self.action_like_answer(incoming_event, button_payload)
        elif button_payload.intent == self.INTENT_BEST_ANSWER:
            return self.action_best_answer_0(incoming_event, button_payload)
        elif button_payload.intent == self.INTENT_ANSWER_NOT:
            return self.action_not_answer_question(incoming_event, button_payload)
        elif button_payload.intent == self.INTENT_ANSWER_QUESTION:
            return self.action_answer_question(incoming_event, button_payload)
        elif button_payload.intent == self.INTENT_ANSWER_REMIND_LATER:
            return self.action_answer_remind_later(incoming_event, button_payload)
        elif button_payload.intent == self.INTENT_ANSWER_PICKED_QUESTION:
            return self.action_answer_picked_question(incoming_event, button_payload)
        else:
            logger.error(f"No action associated with intent [{button_payload.intent}]")
            raise ValueError(f"No action associated with intent [{button_payload.intent}]")

    def handle_wenet_authentication_result(self, message: WeNetAuthenticationEvent) -> NotificationEvent:
        if not isinstance(self._connector, TelegramSocialConnector):
            logger.error(f"Expected telegram social connector, got [{type(self._connector)}]")
            raise Exception(f"Expected telegram social connector, got [{type(self._connector)}]")

        social_details = TelegramDetails(int(message.external_id), int(message.external_id), self._connector.get_telegram_bot_id())
        try:
            self._save_wenet_and_telegram_user_id_to_context(message, social_details)
            user_context = self._interface_connector.get_user_context(social_details)
            messages = self._get_start_messages(self._get_user_locale_from_wenet_id(user_context.context.get_static_state(self.CONTEXT_WENET_USER_ID), context=user_context.context))
            return NotificationEvent(social_details=social_details, messages=messages)
        except Exception as e:
            logger.exception("Unable to complete the WeNet login", exc_info=e)
            return NotificationEvent(social_details).with_message(
                TextualResponse("Unable to complete the WeNetAuthentication")
            )

    def action_question_0(self, incoming_event: IncomingSocialEvent, _: str) -> OutgoingEvent:
        """
        Beginning of the /ask command
        """
        user_locale = self._get_user_locale_from_incoming_event(incoming_event)
        response = OutgoingEvent(social_details=incoming_event.social_details)
        context = incoming_event.context
        context.with_static_state(self.CONTEXT_CURRENT_STATE, self.STATE_QUESTION_0)
        message = self._translator.get_translation_instance(user_locale).with_text("question_1").translate()
        response.with_message(TextualResponse(message))
        response.with_context(context)
        return response

    def action_question_1(self, incoming_event: IncomingSocialEvent, _: str) -> OutgoingEvent:
        """
        Save the question, and ask the domain of the question
        """
        user_locale = self._get_user_locale_from_incoming_event(incoming_event)
        response = OutgoingEvent(social_details=incoming_event.social_details)
        if isinstance(incoming_event.incoming_message, IncomingTextMessage):
            question = self._prepare_string_to_wenet(incoming_event.incoming_message.text)
            context = incoming_event.context
            context.with_static_state(self.CONTEXT_CURRENT_STATE, self.STATE_QUESTION_1)
            context.with_static_state(self.CONTEXT_ASKED_QUESTION, question)
            message = self._translator.get_translation_instance(user_locale).with_text("domain_question").translate()
            button_1_text = self._translator.get_translation_instance(user_locale).with_text("academic_skills_button").translate()
            button_2_text = self._translator.get_translation_instance(user_locale).with_text("basic_needs_button").translate()
            button_3_text = self._translator.get_translation_instance(user_locale).with_text("physical_activity_button").translate()
            button_4_text = self._translator.get_translation_instance(user_locale).with_text("appreciating_culture_button").translate()
            button_5_text = self._translator.get_translation_instance(user_locale).with_text("random_thoughts_button").translate()
            button_6_text = self._translator.get_translation_instance(user_locale).with_text("producing_culture_button").translate()
            button_7_text = self._translator.get_translation_instance(user_locale).with_text("leisure_activities_button").translate()
            button_8_text = self._translator.get_translation_instance(user_locale).with_text("campus_life_button").translate()
            button_9_text = self._translator.get_translation_instance(user_locale).with_text("sensitive_button").translate()
            response_with_buttons = TelegramRapidAnswerResponse(TextualResponse(message), row_displacement=[2, 2, 2, 2, 1])
            response_with_buttons.with_textual_option(button_1_text, self.INTENT_ACADEMIC_SKILLS)
            response_with_buttons.with_textual_option(button_2_text, self.INTENT_BASIC_NEEDS)
            response_with_buttons.with_textual_option(button_3_text, self.INTENT_PHYSICAL_ACTIVITY)
            response_with_buttons.with_textual_option(button_4_text, self.INTENT_APPRECIATING_CULTURE)
            response_with_buttons.with_textual_option(button_5_text, self.INTENT_RANDOM_THOUGHTS)
            response_with_buttons.with_textual_option(button_6_text, self.INTENT_PRODUCING_CULTURE)
            response_with_buttons.with_textual_option(button_7_text, self.INTENT_LEISURE_ACTIVITIES)
            response_with_buttons.with_textual_option(button_8_text, self.INTENT_CAMPUS_LIFE)
            response_with_buttons.with_textual_option(button_9_text, self.INTENT_SENSITIVE_QUESTION)
            response.with_message(response_with_buttons)
            response.with_context(context)
        else:
            error_message = self._translator.get_translation_instance(user_locale).with_text("question_is_not_text").translate()
            response.with_message(TextualResponse(error_message))
        return response

    def action_question_2(self, incoming_event: IncomingSocialEvent, intent: str) -> OutgoingEvent:
        """
        Ask whether to ask the question anonymously or not
        """
        user_locale = self._get_user_locale_from_incoming_event(incoming_event)
        response = OutgoingEvent(social_details=incoming_event.social_details)
        context = incoming_event.context
        context.with_static_state(self.CONTEXT_CURRENT_STATE, self.STATE_QUESTION_2)
        context.with_static_state(self.CONTEXT_QUESTION_DOMAIN, intent)
        if intent == self.INTENT_SENSITIVE_QUESTION:
            message = self._translator.get_translation_instance(user_locale).with_text("sensitive_question_domain").translate()
        else:
            message = self._translator.get_translation_instance(user_locale).with_text("not_sensitive_question_domain").translate()
        response.with_message(TextualResponse(message))
        message = self._translator.get_translation_instance(user_locale).with_text("anonymous_question").translate()
        button_1_text = self._translator.get_translation_instance(user_locale).with_text("anonymous").translate()
        button_2_text = self._translator.get_translation_instance(user_locale).with_text("not_anonymous").translate()
        response_with_buttons = TelegramRapidAnswerResponse(TextualResponse(message), row_displacement=[1, 1])
        response_with_buttons.with_textual_option(button_1_text, self.INTENT_ANONYMOUS_QUESTION)
        response_with_buttons.with_textual_option(button_2_text, self.INTENT_NOT_ANONYMOUS_QUESTION)
        response.with_message(response_with_buttons)
        response.with_context(context)
        return response

    def action_question_3(self, incoming_event: IncomingSocialEvent, intent: str) -> OutgoingEvent:
        """
        Ask whether people that should answer the question should have a similar interest in the domain
        """
        user_locale = self._get_user_locale_from_incoming_event(incoming_event)
        response = OutgoingEvent(social_details=incoming_event.social_details)
        context = incoming_event.context
        context.with_static_state(self.CONTEXT_CURRENT_STATE, self.STATE_QUESTION_3)
        context.with_static_state(self.CONTEXT_ANONYMOUS_QUESTION, intent)
        message = self._translator.get_translation_instance(user_locale).with_text("domain_similarity_question")\
            .with_substitution("domain", self._translator.get_translation_instance(user_locale).with_text(context.get_static_state(self.CONTEXT_QUESTION_DOMAIN)).translate())\
            .translate()
        button_1_text = self._translator.get_translation_instance(user_locale).with_text("answer_similar_domain").translate()
        button_2_text = self._translator.get_translation_instance(user_locale).with_text("answer_different_domain").translate()
        button_3_text = self._translator.get_translation_instance(user_locale).with_text("answer_indifferent_domain").translate()
        response_with_buttons = TelegramRapidAnswerResponse(TextualResponse(message), row_displacement=[2, 1])
        response_with_buttons.with_textual_option(button_1_text, self.INTENT_SIMILAR_DOMAIN)
        response_with_buttons.with_textual_option(button_2_text, self.INTENT_DIFFERENT_DOMAIN)
        response_with_buttons.with_textual_option(button_3_text, self.INTENT_INDIFFERENT_DOMAIN)
        response.with_message(response_with_buttons)
        response.with_context(context)
        return response

    def action_question_4(self, incoming_event: IncomingSocialEvent, intent: str) -> OutgoingEvent:
        """
        Ask whether people that should answer the question should have a similar belief and values
        """
        user_locale = self._get_user_locale_from_incoming_event(incoming_event)
        response = OutgoingEvent(social_details=incoming_event.social_details)
        context = incoming_event.context
        context.with_static_state(self.CONTEXT_CURRENT_STATE, self.STATE_QUESTION_4)
        context.with_static_state(self.CONTEXT_DOMAIN_INTEREST, intent)
        message = self._translator.get_translation_instance(user_locale).with_text("belief_values_question").translate()
        button_1_text = self._translator.get_translation_instance(user_locale).with_text("answer_similar_belief_values").translate()
        button_2_text = self._translator.get_translation_instance(user_locale).with_text("answer_different_belief_values").translate()
        button_3_text = self._translator.get_translation_instance(user_locale).with_text("answer_indifferent_belief_values").translate()
        response_with_buttons = TelegramRapidAnswerResponse(TextualResponse(message), row_displacement=[2, 1])
        response_with_buttons.with_textual_option(button_1_text, self.INTENT_SIMILAR_BELIEF_VALUES)
        response_with_buttons.with_textual_option(button_2_text, self.INTENT_DIFFERENT_BELIEF_VALUES)
        response_with_buttons.with_textual_option(button_3_text, self.INTENT_INDIFFERENT_BELIEF_VALUES)
        response.with_message(response_with_buttons)
        response.with_context(context)
        return response

    def action_question_5(self, incoming_event: IncomingSocialEvent, intent: str) -> OutgoingEvent:
        """
        Ask whether people that should answer the question should be socially closer
        """
        user_locale = self._get_user_locale_from_incoming_event(incoming_event)
        response = OutgoingEvent(social_details=incoming_event.social_details)
        context = incoming_event.context
        context.with_static_state(self.CONTEXT_CURRENT_STATE, self.STATE_QUESTION_5)
        context.with_static_state(self.CONTEXT_BELIEF_VALUES_SIMILARITY, intent)
        message = self._translator.get_translation_instance(user_locale).with_text("social_closeness_question").translate()
        button_1_text = self._translator.get_translation_instance(user_locale).with_text("answer_socially_close").translate()
        button_2_text = self._translator.get_translation_instance(user_locale).with_text("answer_socially_distant").translate()
        button_3_text = self._translator.get_translation_instance(user_locale).with_text("answer_socially_indifferent").translate()
        response_with_buttons = TelegramRapidAnswerResponse(TextualResponse(message), row_displacement=[2, 1])
        response_with_buttons.with_textual_option(button_1_text, self.INTENT_SIMILAR_SOCIALLY)
        response_with_buttons.with_textual_option(button_2_text, self.INTENT_DIFFERENT_SOCIALLY)
        response_with_buttons.with_textual_option(button_3_text, self.INTENT_INDIFFERENT_SOCIALLY)
        response.with_message(response_with_buttons)
        response.with_context(context)
        return response

    def action_question_6(self, incoming_event: IncomingSocialEvent, intent: str) -> OutgoingEvent:
        """
        Ask where should be the people that should answer the question
        """
        user_locale = self._get_user_locale_from_incoming_event(incoming_event)
        response = OutgoingEvent(social_details=incoming_event.social_details)
        context = incoming_event.context
        context.with_static_state(self.CONTEXT_CURRENT_STATE, self.STATE_QUESTION_6)
        context.with_static_state(self.CONTEXT_SOCIAL_CLOSENESS, intent)
        message = self._translator.get_translation_instance(user_locale).with_text("specify_answerer_location").translate()
        button_1_text = self._translator.get_translation_instance(user_locale).with_text("location_answer_1").translate()
        button_2_text = self._translator.get_translation_instance(user_locale).with_text("location_answer_2").translate()
        response_with_buttons = TelegramRapidAnswerResponse(TextualResponse(message), row_displacement=[1, 1])
        response_with_buttons.with_textual_option(button_1_text, self.INTENT_ASK_TO_NEARBY)
        response_with_buttons.with_textual_option(button_2_text, self.INTENT_ASK_TO_ANYWHERE)
        response.with_message(response_with_buttons)
        response.with_context(context)
        return response

    def action_question_final(self, incoming_event: IncomingSocialEvent, intent: str) -> OutgoingEvent:
        """
        Conclude the /ask flow, with a final message
        """
        if incoming_event.context is not None:
            service_api = self._get_service_api_interface_connector_from_context(incoming_event.context)
        else:
            raise Exception(f"Missing conversation context for event {incoming_event}")
        user_locale = self._get_user_locale_from_incoming_event(incoming_event)
        response = OutgoingEvent(social_details=incoming_event.social_details)
        context = incoming_event.context
        if not context.has_static_state(self.CONTEXT_ASKED_QUESTION) \
                or not context.has_static_state(self.CONTEXT_QUESTION_DOMAIN) \
                or not context.has_static_state(self.CONTEXT_ANONYMOUS_QUESTION) \
                or not context.has_static_state(self.CONTEXT_DOMAIN_INTEREST) \
                or not context.has_static_state(self.CONTEXT_BELIEF_VALUES_SIMILARITY) \
                or not context.has_static_state(self.CONTEXT_SOCIAL_CLOSENESS):
            logger.error(f"Expected {self.CONTEXT_ASKED_QUESTION}, {self.CONTEXT_QUESTION_DOMAIN}, {self.CONTEXT_ANONYMOUS_QUESTION}, {self.CONTEXT_DOMAIN_INTEREST}, {self.CONTEXT_BELIEF_VALUES_SIMILARITY}, {self.CONTEXT_SOCIAL_CLOSENESS} in the context")
            raise Exception(f"Expected {self.CONTEXT_ASKED_QUESTION}, {self.CONTEXT_QUESTION_DOMAIN}, {self.CONTEXT_ANONYMOUS_QUESTION}, {self.CONTEXT_DOMAIN_INTEREST}, {self.CONTEXT_BELIEF_VALUES_SIMILARITY}, {self.CONTEXT_SOCIAL_CLOSENESS} in the context")
        wenet_id = context.get_static_state(self.CONTEXT_WENET_USER_ID)
        question = context.get_static_state(self.CONTEXT_ASKED_QUESTION)
        domain = context.get_static_state(self.CONTEXT_QUESTION_DOMAIN)
        anonymous = True if context.get_static_state(self.CONTEXT_ANONYMOUS_QUESTION) == self.INTENT_ANONYMOUS_QUESTION else False
        domain_interest = context.get_static_state(self.CONTEXT_DOMAIN_INTEREST)
        belief_values_similarity = context.get_static_state(self.CONTEXT_BELIEF_VALUES_SIMILARITY)
        social_closeness = context.get_static_state(self.CONTEXT_SOCIAL_CLOSENESS)
        expiration_date = datetime.now() + timedelta(seconds=self.neaby_expiration_duration if intent == self.INTENT_ASK_TO_NEARBY else self.expiration_duration)
        attributes = {
            "domain": domain,
            "anonymous": anonymous,
            "domainInterest": domain_interest,
            "beliefsAndValues": belief_values_similarity,
            "socialCloseness": social_closeness,
            "positionOfAnswerer": intent,
            "maxUsers": self.max_users,
            "maxAnswers": self.max_answers,
            "expirationDate": int(expiration_date.timestamp())
        }
        question_task = Task(
            None,
            int(datetime.now().timestamp()),
            int(datetime.now().timestamp()),
            str(self.task_type_id),
            str(wenet_id),
            self.app_id,
            self.community_id,
            TaskGoal(question, ""),
            [],
            attributes,
            None,
            []
        )
        try:
            service_api.create_task(question_task)
            logger.debug(f"User [{wenet_id}] asked a question. Task created successfully")
            message = self._translator.get_translation_instance(user_locale) \
                .with_text("question_final") \
                .with_substitution("expiration_duration", str(int(self.neaby_expiration_duration / 3600)) if intent == self.INTENT_ASK_TO_NEARBY else str(int(self.expiration_duration / 3600))) \
                .translate()
            response.with_message(TextualResponse(message))
        except CreationError as e:
            logger.error(f"The service API responded with code {e.http_status_code} and message {json.dumps(e.server_response)}")
            message = self._translator.get_translation_instance(user_locale).with_text("error_task_creation").translate()
            response.with_message(TextualResponse(message))
        finally:
            context.delete_static_state(self.CONTEXT_ASKED_QUESTION)
            context.delete_static_state(self.CONTEXT_QUESTION_DOMAIN)
            context.delete_static_state(self.CONTEXT_ANONYMOUS_QUESTION)
            context.delete_static_state(self.CONTEXT_DOMAIN_INTEREST)
            context.delete_static_state(self.CONTEXT_BELIEF_VALUES_SIMILARITY)
            context.delete_static_state(self.CONTEXT_SOCIAL_CLOSENESS)
            context.delete_static_state(self.CONTEXT_CURRENT_STATE)
            response.with_context(context)
        return response

    def _is_first_answer(self, wenet_user_id: str) -> bool:
        """
        Use Redis to keep track of the fact that a WeNet user has already answered someone else's question.
        This piece of information is used to decide whether or not showing the conduct instructions
        """
        first_answer = self.cache.get(self.FIRST_ANSWER.format(wenet_user_id))
        if first_answer is None:
            self.cache.cache({"has_answered": True}, key=self.FIRST_ANSWER.format(wenet_user_id))
            return True
        return False

    def action_answer_question(self, incoming_event: IncomingSocialEvent, button_payload: ButtonPayload) -> OutgoingEvent:
        """
        QuestionToAnswerMessage flow, when user click on the answer button
        """
        user_locale = self._get_user_locale_from_incoming_event(incoming_event)
        context = incoming_event.context
        user_id = context.get_static_state(self.CONTEXT_WENET_USER_ID)
        show_conduct_message = True
        if user_id:
            is_first_answer = self._is_first_answer(user_id)
            show_conduct_message = is_first_answer or random.randint(1, 10) <= 2
        context.with_static_state(self.CONTEXT_QUESTION_TO_ANSWER, button_payload.payload["task_id"])
        if button_payload.payload.get("sensitive", False):
            context.with_static_state(self.CONTEXT_CURRENT_STATE, self.STATE_ANSWERING_SENSITIVE)
            message = self._translator.get_translation_instance(user_locale).with_text("answer_sensitive_question").translate()
        else:
            context.with_static_state(self.CONTEXT_CURRENT_STATE, self.STATE_ANSWERING)
            message = self._translator.get_translation_instance(user_locale).with_text("answer_question").translate()

        response = OutgoingEvent(social_details=incoming_event.social_details)
        response.with_context(context)
        response.with_message(TextualResponse(message))
        if show_conduct_message:
            if self.helper_url:
                conduct_message = self._translator.get_translation_instance(user_locale).with_text("question_0_with_helper_url") \
                    .with_substitution("helper_url", self.helper_url) \
                    .translate()
            else:
                conduct_message = self._translator.get_translation_instance(user_locale).with_text("question_0").translate()
            response.with_message(TextualResponse(conduct_message))
        return response

    def action_answer_picked_question(self, incoming_event: IncomingSocialEvent, button_payload: ButtonPayload) -> OutgoingEvent:
        """
        /questions flow, when the user picks a question to answer to
        """
        if incoming_event.context is not None:
            service_api = self._get_service_api_interface_connector_from_context(incoming_event.context)
        else:
            raise Exception(f"Missing conversation context for event {incoming_event}")

        user_locale = self._get_user_locale_from_incoming_event(incoming_event)
        context = incoming_event.context
        context.with_static_state(self.CONTEXT_QUESTION_TO_ANSWER, button_payload.payload["task_id"])
        user_id = context.get_static_state(self.CONTEXT_WENET_USER_ID)
        task = service_api.get_task(button_payload.payload["task_id"])

        if button_payload.payload.get("sensitive", False):
            context.with_static_state(self.CONTEXT_CURRENT_STATE, self.STATE_ANSWERING_SENSITIVE)
            message = self._translator.get_translation_instance(user_locale).with_text("you_are_answering_to_sensitive")\
                .with_substitution("question", self.parse_text_with_markdown(self._prepare_string_to_telegram(task.goal.name)))\
                .translate()
        else:
            context.with_static_state(self.CONTEXT_CURRENT_STATE, self.STATE_ANSWERING)
            message = self._translator.get_translation_instance(user_locale).with_text("you_are_answering_to")\
                .with_substitution("question", self.parse_text_with_markdown(self._prepare_string_to_telegram(task.goal.name)))\
                .translate()

        response = OutgoingEvent(social_details=incoming_event.social_details)
        response.with_context(context)
        response.with_message(TextualResponse(message))
        is_first_time = self._is_first_answer(user_id)
        if is_first_time:
            if self.helper_url:
                conduct_message = self._translator.get_translation_instance(user_locale).with_text("question_0_with_helper_url") \
                    .with_substitution("helper_url", self.helper_url) \
                    .translate()
            else:
                conduct_message = self._translator.get_translation_instance(user_locale).with_text("question_0").translate()
            response.with_message(TextualResponse(conduct_message))
        return response

    def action_answer_sensitive_question(self, incoming_event: IncomingSocialEvent, _: str) -> OutgoingEvent:
        """
        QuestionToAnswerMessage flow, collect the user's answer and since it is a sensitive question ask if should be anonymous the answer
        """
        user_locale = self._get_user_locale_from_incoming_event(incoming_event)
        context = incoming_event.context
        if not context.has_static_state(self.CONTEXT_QUESTION_TO_ANSWER):
            logger.error("Illegal state, expected the question ID in the context, but it does not exist")
            raise ValueError("Illegal state, expected the question ID in the context, but it does not exist")

        response = OutgoingEvent(social_details=incoming_event.social_details)
        if isinstance(incoming_event.incoming_message, IncomingTextMessage):
            context.with_static_state(self.CONTEXT_CURRENT_STATE, self.STATE_ANSWERING_ANONYMOUSLY)
            context.with_static_state(self.CONTEXT_ANSWER_TO_QUESTION, self._prepare_string_to_wenet(incoming_event.incoming_message.text))
            message = self._translator.get_translation_instance(user_locale).with_text("answer_anonymously").translate()
            button_1_text = self._translator.get_translation_instance(user_locale).with_text("anonymous_answer_1").translate()
            button_2_text = self._translator.get_translation_instance(user_locale).with_text("anonymous_answer_2").translate()
            response_with_buttons = TelegramRapidAnswerResponse(TextualResponse(message), row_displacement=[2])
            response_with_buttons.with_textual_option(button_1_text, self.INTENT_ANSWER_ANONYMOUSLY)
            response_with_buttons.with_textual_option(button_2_text, self.INTENT_ANSWER_NOT_ANONYMOUSLY)
            response.with_message(response_with_buttons)
            response.with_context(context)
        else:
            error_message = self._translator.get_translation_instance(user_locale).with_text("answerer_is_not_text").translate()
            response.with_message(TextualResponse(error_message))
        return response

    def action_answer_question_anonymously(self, incoming_event: IncomingSocialEvent, intent: str) -> OutgoingEvent:
        """
        QuestionToAnswerMessage flow, collect if the user's answer should be anonymous and thank her
        """
        user_locale = self._get_user_locale_from_incoming_event(incoming_event)
        context = incoming_event.context
        response = OutgoingEvent(social_details=incoming_event.social_details)
        if intent == self.INTENT_ANSWER_ANONYMOUSLY:
            message = self._translator.get_translation_instance(user_locale).with_text("answered_message_anonymously").translate()
            context.with_static_state(self.CONTEXT_ANONYMOUS_ANSWER, True)
        else:
            message = self._translator.get_translation_instance(user_locale).with_text("answered_message").translate()
            context.with_static_state(self.CONTEXT_ANONYMOUS_ANSWER, False)

        context.with_static_state(self.CONTEXT_CURRENT_STATE, self.STATE_PUBLISHING_ANSWER_TO_CHANNEL)
        if self.channel_id:
            response.with_message(TextualResponse(message))
            message_text = self._translator.get_translation_instance(user_locale).with_text("ok_to_publish_message").translate()
            button_1_text = self._translator.get_translation_instance(user_locale).with_text("button_yes_anonymously_publish_text").translate()
            button_2_text = self._translator.get_translation_instance(user_locale).with_text("button_yes_name_publish_text").translate()
            button_3_text = self._translator.get_translation_instance(user_locale).with_text("button_no_publish_text").translate()
            message_response = TelegramRapidAnswerResponse(TextualResponse(message_text), row_displacement=[1, 1, 1])
            message_response.with_textual_option(button_1_text, self.INTENT_AGREE_PUBLISH_ANONYMOUSLY)
            message_response.with_textual_option(button_2_text, self.INTENT_AGREE_PUBLISH_NAME)
            message_response.with_textual_option(button_3_text, self.INTENT_NOT_AGREE_PUBLISH)
            response.with_message(message_response)
        else:
            if incoming_event.context is not None:
                service_api = self._get_service_api_interface_connector_from_context(incoming_event.context)
            else:
                raise Exception(f"Missing conversation context for event {incoming_event}")

            question_id = context.get_static_state(self.CONTEXT_QUESTION_TO_ANSWER)
            answer = context.get_static_state(self.CONTEXT_ANSWER_TO_QUESTION)
            anonymous = context.with_static_state(self.CONTEXT_ANONYMOUS_ANSWER, True)
            actioneer_id = context.get_static_state(self.CONTEXT_WENET_USER_ID)
            try:
                transaction = TaskTransaction(None, question_id, self.LABEL_ANSWER_TRANSACTION, int(datetime.now().timestamp()), int(datetime.now().timestamp()), actioneer_id, {"answer": answer, "anonymous": anonymous, "publish": False, "publishAnonymously": False}, [])
                service_api.create_task_transaction(transaction)
                logger.info("Sent task transaction: %s" % str(transaction.to_repr()))
                response.with_message(TextualResponse(message))
            except CreationError as e:
                response.with_message(TextualResponse(self._translator.get_translation_instance(user_locale).with_text("error_task_creation").translate()))
                logger.error(
                    "Error in the creation of the transaction for answering the task [%s]. The service API responded with code %d and message %s"
                    % (question_id, e.http_status_code, json.dumps(e.server_response))
                )
            finally:
                context.delete_static_state(self.CONTEXT_QUESTION_TO_ANSWER)
                context.delete_static_state(self.CONTEXT_ANSWER_TO_QUESTION)
                context.delete_static_state(self.CONTEXT_ANONYMOUS_ANSWER)
                context.delete_static_state(self.CONTEXT_CURRENT_STATE)

        response.with_context(context)
        return response

    def action_answer_question_2(self, incoming_event: IncomingSocialEvent, _: str) -> OutgoingEvent:
        """
        QuestionToAnswerMessage flow, collect the user's answer and thank her
        """
        user_locale = self._get_user_locale_from_incoming_event(incoming_event)
        context = incoming_event.context
        response = OutgoingEvent(social_details=incoming_event.social_details)
        if isinstance(incoming_event.incoming_message, IncomingTextMessage):
            answer = self._prepare_string_to_wenet(incoming_event.incoming_message.text)
            message = self._translator.get_translation_instance(user_locale).with_text("answered_message").translate()
            response.with_message(TextualResponse(message))

            if self.channel_id:
                context.with_static_state(self.CONTEXT_ANSWER_TO_QUESTION, answer)
                context.with_static_state(self.CONTEXT_ANONYMOUS_ANSWER, False)
                context.with_static_state(self.CONTEXT_CURRENT_STATE, self.STATE_PUBLISHING_ANSWER_TO_CHANNEL)
                message_text = self._translator.get_translation_instance(user_locale).with_text("ok_to_publish_message").translate()
                button_1_text = self._translator.get_translation_instance(user_locale).with_text("button_yes_anonymously_publish_text").translate()
                button_2_text = self._translator.get_translation_instance(user_locale).with_text("button_yes_name_publish_text").translate()
                button_3_text = self._translator.get_translation_instance(user_locale).with_text("button_no_publish_text").translate()
                message_response = TelegramRapidAnswerResponse(TextualResponse(message_text), row_displacement=[1, 1, 1])
                message_response.with_textual_option(button_1_text, self.INTENT_AGREE_PUBLISH_ANONYMOUSLY)
                message_response.with_textual_option(button_2_text, self.INTENT_AGREE_PUBLISH_NAME)
                message_response.with_textual_option(button_3_text, self.INTENT_NOT_AGREE_PUBLISH)
                response.with_message(message_response)
            else:
                if incoming_event.context is not None:
                    service_api = self._get_service_api_interface_connector_from_context(incoming_event.context)
                else:
                    raise Exception(f"Missing conversation context for event {incoming_event}")

                question_id = context.get_static_state(self.CONTEXT_QUESTION_TO_ANSWER)
                answer = context.get_static_state(self.CONTEXT_ANSWER_TO_QUESTION)
                actioneer_id = context.get_static_state(self.CONTEXT_WENET_USER_ID)
                try:
                    transaction = TaskTransaction(None, question_id, self.LABEL_ANSWER_TRANSACTION, int(datetime.now().timestamp()), int(datetime.now().timestamp()), actioneer_id, {"answer": answer, "anonymous": False, "publish": False, "publishAnonymously": False}, [])
                    service_api.create_task_transaction(transaction)
                    logger.info("Sent task transaction: %s" % str(transaction.to_repr()))
                except CreationError as e:
                    response.with_message(TextualResponse(self._translator.get_translation_instance(user_locale).with_text("error_task_creation").translate()))
                    logger.error(
                        "Error in the creation of the transaction for answering the task [%s]. The service API responded with code %d and message %s"
                        % (question_id, e.http_status_code, json.dumps(e.server_response))
                    )
                finally:
                    context.delete_static_state(self.CONTEXT_QUESTION_TO_ANSWER)
                    context.delete_static_state(self.CONTEXT_ANSWER_TO_QUESTION)
                    context.delete_static_state(self.CONTEXT_CURRENT_STATE)

            response.with_context(context)
        else:
            error_message = self._translator.get_translation_instance(user_locale).with_text("answerer_is_not_text").translate()
            response.with_message(TextualResponse(error_message))
        return response

    def action_agree_to_publish(self, incoming_event: IncomingSocialEvent, intent: str) -> OutgoingEvent:
        if incoming_event.context is not None:
            service_api = self._get_service_api_interface_connector_from_context(incoming_event.context)
        else:
            raise Exception(f"Missing conversation context for event {incoming_event}")

        user_locale = self._get_user_locale_from_incoming_event(incoming_event)
        context = incoming_event.context

        response = OutgoingEvent(social_details=incoming_event.social_details)
        question_id = context.get_static_state(self.CONTEXT_QUESTION_TO_ANSWER)
        answer = context.get_static_state(self.CONTEXT_ANSWER_TO_QUESTION)
        anonymous = context.get_static_state(self.CONTEXT_ANONYMOUS_ANSWER)
        actioneer_id = context.get_static_state(self.CONTEXT_WENET_USER_ID)
        try:
            transaction = TaskTransaction(
                transaction_id=None,
                task_id=question_id,
                label=self.LABEL_ANSWER_TRANSACTION,
                creation_ts=int(datetime.now().timestamp()),
                last_update_ts=int(datetime.now().timestamp()),
                actioneer_id=actioneer_id,
                attributes={
                    "answer": answer,
                    "anonymous": anonymous,
                    "publish": True if intent == self.INTENT_AGREE_PUBLISH_NAME or intent == self.INTENT_AGREE_PUBLISH_ANONYMOUSLY else False,
                    "publishAnonymously": True if intent == self.INTENT_AGREE_PUBLISH_ANONYMOUSLY else False
                },
                messages=[]
            )
            service_api.create_task_transaction(transaction)
            logger.info("Sent task transaction: %s" % str(transaction.to_repr()))
            message = self._translator.get_translation_instance(user_locale).with_text("thank_you_message").translate()
            response.with_message(TextualResponse(message))
        except CreationError as e:
            response.with_message(TextualResponse(self._translator.get_translation_instance(user_locale).with_text("error_task_creation").translate()))
            logger.error(
                "Error in the creation of the transaction for answering the task [%s]. The service API responded with code %d and message %s"
                % (question_id, e.http_status_code, json.dumps(e.server_response))
            )
        finally:
            context.delete_static_state(self.CONTEXT_QUESTION_TO_ANSWER)
            context.delete_static_state(self.CONTEXT_ANSWER_TO_QUESTION)
            context.delete_static_state(self.CONTEXT_CURRENT_STATE)
            context.delete_static_state(self.CONTEXT_ANONYMOUS_ANSWER)
            response.with_context(context)
        return response

    def action_not_answer_question(self, incoming_event: IncomingSocialEvent, button_payload: ButtonPayload) -> OutgoingEvent:
        response = OutgoingEvent(social_details=incoming_event.social_details)
        user_locale = self._get_user_locale_from_incoming_event(incoming_event)
        if incoming_event.context is not None:
            service_api = self._get_service_api_interface_connector_from_context(incoming_event.context)
        else:
            raise Exception(f"Missing conversation context for event {incoming_event}")
        context = incoming_event.context
        question_id = button_payload.payload["task_id"]
        actioneer_id = context.get_static_state(self.CONTEXT_WENET_USER_ID)
        try:
            transaction = TaskTransaction(None, question_id, self.LABEL_NOT_ANSWER_TRANSACTION, int(datetime.now().timestamp()), int(datetime.now().timestamp()), actioneer_id, {}, [])
            service_api.create_task_transaction(transaction)
            message = self._translator.get_translation_instance(user_locale).with_text("not_answer_response").translate()
            response.with_message(TextualResponse(message))
        except CreationError as e:
            response.with_message(TextualResponse(self._translator.get_translation_instance(user_locale).with_text("error_task_creation").translate()))
            logger.error(
                "Error in the creation of the transaction for not answering the task [%s]. The service API responded with code %d and message %s"
                % (question_id, e.http_status_code, json.dumps(e.server_response))
            )
        response.with_context(context)
        return response

    def action_answer_remind_later(self, incoming_event: IncomingSocialEvent, button_payload: ButtonPayload) -> OutgoingEvent:
        response = OutgoingEvent(social_details=incoming_event.social_details)
        user_locale = self._get_user_locale_from_incoming_event(incoming_event)
        context = incoming_event.context
        message = self._translator.get_translation_instance(user_locale).with_text("answer_remind_later_message").translate()
        response.with_message(TextualResponse(message))
        pending_answers = context.get_static_state(self.CONTEXT_PENDING_ANSWERS, dict())
        question_id = button_payload.payload["task_id"]

        # Recreating the message that someone in the community has a question and insert the details of the question, treat differently sensitive questions
        message_string = self._translator.get_translation_instance(user_locale)
        if button_payload.payload.get("sensitive"):
            message_string = message_string.with_text("answer_sensitive_message_0")
        else:
            message_string = message_string.with_text("answer_message_0")

        message_string = message_string.with_substitution("question", self.parse_text_with_markdown(button_payload.payload["question"])) \
            .with_substitution("user", button_payload.payload["username"]) \
            .translate()

        button_ids = [str(uuid.uuid4()) for _ in range(4)]
        button_data = {
            "task_id": question_id,
            "question": button_payload.payload["question"],
            "sensitive": button_payload.payload.get("sensitive", False),
            "username": button_payload.payload["username"],
            "related_buttons": button_ids,
        }
        response_to_store = TelegramRapidAnswerResponse(TextualResponse(message_string), row_displacement=[2, 2])

        self.cache.cache(ButtonPayload(button_data, self.INTENT_ANSWER_QUESTION).to_repr(), key=button_ids[0])
        response_to_store.with_textual_option(self._translator.get_translation_instance(user_locale).with_text("answer_question_button").translate(), self.INTENT_BUTTON_WITH_PAYLOAD.format(button_ids[0]))
        self.cache.cache(ButtonPayload(button_data, self.INTENT_ANSWER_REMIND_LATER).to_repr(), key=button_ids[1])
        response_to_store.with_textual_option(self._translator.get_translation_instance(user_locale).with_text("answer_remind_later_button").translate(), self.INTENT_BUTTON_WITH_PAYLOAD.format(button_ids[1]))
        self.cache.cache(ButtonPayload(button_data, self.INTENT_ANSWER_NOT).to_repr(), key=button_ids[2])
        response_to_store.with_textual_option(self._translator.get_translation_instance(user_locale).with_text("answer_not_button").translate(), self.INTENT_BUTTON_WITH_PAYLOAD.format(button_ids[2]))
        self.cache.cache(ButtonPayload(button_data, self.INTENT_QUESTION_REPORT).to_repr(), key=button_ids[3])
        response_to_store.with_textual_option(self._translator.get_translation_instance(user_locale).with_text("answer_report_button").translate(), self.INTENT_BUTTON_WITH_PAYLOAD.format(button_ids[3]))
        pending_answer = PendingQuestionToAnswer(question_id, response_to_store, incoming_event.social_details, sent=datetime.now(), response_to=incoming_event.incoming_message.message_id)
        pending_answers[question_id] = pending_answer.to_repr()
        context.with_static_state(self.CONTEXT_PENDING_ANSWERS, pending_answers)
        response.with_context(context)
        return response

    def action_report_message(self, incoming_event: IncomingSocialEvent, button_payload: ButtonPayload) -> OutgoingEvent:
        """
        First step of reporting a single message (either a question or an answer).
        The payload must have the task id, and in case of reporting an answer it has also the transaction id
        """
        response = OutgoingEvent(social_details=incoming_event.social_details)
        user_locale = self._get_user_locale_from_incoming_event(incoming_event)
        message_text = self._translator.get_translation_instance(user_locale).with_text("why_reporting_message").translate()
        button_why_reporting_1_text = self._translator.get_translation_instance(user_locale).with_text("button_why_reporting_1_text").translate()
        button_why_reporting_2_text = self._translator.get_translation_instance(user_locale).with_text("button_why_reporting_2_text").translate()
        button_why_reporting_3_text = self._translator.get_translation_instance(user_locale).with_text("button_why_reporting_3_text").translate()
        message = TelegramRapidAnswerResponse(TextualResponse(message_text), row_displacement=[2, 1])
        button_ids = [str(uuid.uuid4()) for _ in range(2)]
        payload = button_payload.payload
        payload.update({"related_buttons": button_ids})
        self.cache.cache(ButtonPayload(button_payload.payload, self.INTENT_REPORT_ABUSIVE).to_repr(), key=button_ids[0])
        self.cache.cache(ButtonPayload(button_payload.payload, self.INTENT_REPORT_SPAM).to_repr(), key=button_ids[1])
        message.with_textual_option(button_why_reporting_1_text, self.INTENT_BUTTON_WITH_PAYLOAD.format(button_ids[0]))
        message.with_textual_option(button_why_reporting_2_text, self.INTENT_BUTTON_WITH_PAYLOAD.format(button_ids[1]))
        message.with_textual_option(button_why_reporting_3_text, self.INTENT_CANCEL)
        response.with_message(message)
        return response

    def action_report_message_1(self, incoming_event: IncomingSocialEvent, button_payload: ButtonPayload) -> OutgoingEvent:
        """
        Second step of reporting a single message (either a question or an answer).
        A transaction is sent
        """
        response = OutgoingEvent(social_details=incoming_event.social_details)
        user_locale = self._get_user_locale_from_incoming_event(incoming_event)
        task_id = button_payload.payload["task_id"]
        transaction_id = button_payload.payload.get("transaction_id", None)
        if incoming_event.context is not None:
            service_api = self._get_service_api_interface_connector_from_context(incoming_event.context)
        else:
            raise Exception(f"Missing conversation context for event {incoming_event}")

        attributes = {
            "reason": button_payload.intent,
        }
        if transaction_id is None:
            transaction_label = self.LABEL_REPORT_QUESTION_TRANSACTION
        else:
            transaction_label = self.LABEL_REPORT_ANSWER_TRANSACTION
            attributes.update({"transactionId": transaction_id})
        actioneer_id = incoming_event.context.get_static_state(self.CONTEXT_WENET_USER_ID)
        try:
            transaction = TaskTransaction(None, task_id, transaction_label, int(datetime.now().timestamp()), int(datetime.now().timestamp()), actioneer_id, attributes, [])
            service_api.create_task_transaction(transaction)
            logger.info("Sent task transaction: %s" % str(transaction.to_repr()))
            message = self._translator.get_translation_instance(user_locale).with_text("report_final_message").translate()
            response.with_message(TextualResponse(message))
        except CreationError as e:
            response.with_message(TextualResponse(self._translator.get_translation_instance(user_locale).with_text("error_task_creation").translate()))
            logger.error(
                "Error in the creation of the transaction for reporting the task [%s]. The service API responded with code %d and message %s"
                % (task_id, e.http_status_code, json.dumps(e.server_response))
            )
        return response

    def action_more_answers(self, incoming_event: IncomingSocialEvent, button_payload: ButtonPayload) -> OutgoingEvent:
        response = OutgoingEvent(social_details=incoming_event.social_details)
        user_locale = self._get_user_locale_from_incoming_event(incoming_event)
        context = incoming_event.context
        if context is not None:
            service_api = self._get_service_api_interface_connector_from_context(incoming_event.context)
        else:
            raise Exception(f"Missing conversation context for event {incoming_event}")

        task_id = button_payload.payload["task_id"]

        task = service_api.get_task(task_id)
        expiration_date = datetime.fromtimestamp(task.attributes.get("expirationDate")) + timedelta(seconds=self.neaby_expiration_duration if task.attributes.get("positionOfAnswerer") == self.INTENT_ASK_TO_NEARBY else self.expiration_duration)
        expiration = int(expiration_date.timestamp())

        actioneer_id = context.get_static_state(self.CONTEXT_WENET_USER_ID)
        try:
            transaction = TaskTransaction(None, task_id, self.LABEL_MORE_ANSWER_TRANSACTION, int(datetime.now().timestamp()), int(datetime.now().timestamp()), actioneer_id, {
                "expirationDate": expiration
            }, [])
            service_api.create_task_transaction(transaction)
            logger.info("Sent task transaction: %s" % str(transaction.to_repr()))
            message = self._translator.get_translation_instance(user_locale).with_text("ask_more_answers_text").translate()
            response.with_message(TextualResponse(message))
        except CreationError as e:
            response.with_message(TextualResponse(self._translator.get_translation_instance(user_locale).with_text("error_task_creation").translate()))
            logger.error(
                "Error in the creation of the transaction to ask more responses for the task [%s]. The service API responded with code %d and message %s"
                % (task_id, e.http_status_code, json.dumps(e.server_response))
            )

        response.with_context(context)
        return response

    def _get_telegram_user(self, context: ConversationContext) -> Optional[str]:
        if not isinstance(self._connector, TelegramSocialConnector):
            logger.error(f"Expected telegram social connector, got [{type(self._connector)}]")
            raise Exception(f"Expected telegram social connector, got [{type(self._connector)}]")

        response = requests.get(f"{getattr(self._connector, '_telegram_url')}/getChat?chat_id={context.get_static_state(self.CONTEXT_TELEGRAM_USER_ID)}")
        username = response.json()['result'].get('username', None)
        if username is not None:  # The username could not available since is not mandatory to have it
            username = f"@{username}"
            return username.replace("_", "\\_").replace("*", "\\*").replace("`", "\\`")
        else:
            return username

    def action_follow_up_0(self, incoming_event: IncomingSocialEvent, button_payload: ButtonPayload) -> OutgoingEvent:
        response = OutgoingEvent(social_details=incoming_event.social_details)
        user_locale = self._get_user_locale_from_incoming_event(incoming_event)
        context = incoming_event.context
        if self._get_telegram_user(context):
            context.with_static_state(self.CONTEXT_CURRENT_STATE, self.STATE_FOLLOW_UP_0)
            context.with_static_state(self.CONTEXT_ANSWERER_USER_ID, button_payload.payload["answerer_user_id"])
            context.with_static_state(self.CONTEXT_ANSWERER_NAME, button_payload.payload["answerer_name"])
            context.with_static_state(self.CONTEXT_ANSWER_RECEIVED, button_payload.payload["answer"])
            context.with_static_state(self.CONTEXT_TASK_ID, button_payload.payload["task_id"])
            context.with_static_state(self.CONTEXT_TRANSACTION_ID, button_payload.payload["transaction_id"])
            context.with_static_state(self.CONTEXT_QUESTIONER_USER_ID, button_payload.payload["questioner_user_id"])
            context.with_static_state(self.CONTEXT_QUESTION_ANSWERED, button_payload.payload["question"])

            message = self._translator.get_translation_instance(user_locale).with_text("share_details_for_follow_up").with_substitution("answerer", button_payload.payload["answerer_name"]).translate()
            button_1_text = self._translator.get_translation_instance(user_locale).with_text("share_details").translate()
            button_2_text = self._translator.get_translation_instance(user_locale).with_text("not_share_details").translate()
            message = TelegramRapidAnswerResponse(TextualResponse(message), row_displacement=[1, 1])
            message.with_textual_option(button_1_text, self.INTENT_SHARE_DETAILS)
            message.with_textual_option(button_2_text, self.INTENT_NOT_SHARE_DETAILS)

        else:  # if there is no username on Telegram when he wants to share it: ask to set username sending to him the telegram instruction in order to set it
            message = self._translator.get_translation_instance(user_locale).with_text("set_telegram_username").translate()
            message = TelegramRapidAnswerResponse(TextualResponse(message), row_displacement=[1])
            button_follow_up_text = self._translator.get_translation_instance(user_locale).with_text("follow_up_button").with_substitution("answerer", button_payload.payload["answerer_name"]).translate()
            button_id = str(uuid.uuid4())
            self.cache.cache(ButtonPayload(button_payload.payload, self.INTENT_FOLLOW_UP).to_repr(), key=button_id)
            message.with_textual_option(button_follow_up_text, self.INTENT_BUTTON_WITH_PAYLOAD.format(button_id))

        response.with_message(message)
        response.with_context(context)
        return response

    def action_follow_up_1(self, incoming_event: IncomingSocialEvent, intent: str) -> OutgoingEvent:
        response = OutgoingEvent(social_details=incoming_event.social_details)
        user_locale = self._get_user_locale_from_incoming_event(incoming_event)

        context = incoming_event.context
        answerer_user_id = context.get_static_state(self.CONTEXT_ANSWERER_USER_ID)
        answerer_name = context.get_static_state(self.CONTEXT_ANSWERER_NAME)
        answer = context.get_static_state(self.CONTEXT_ANSWER_RECEIVED)
        task_id = context.get_static_state(self.CONTEXT_TASK_ID)
        transaction_id = context.get_static_state(self.CONTEXT_TRANSACTION_ID)
        questioner_user_id = context.get_static_state(self.CONTEXT_QUESTIONER_USER_ID)
        question = context.get_static_state(self.CONTEXT_QUESTION_ANSWERED)
        context.delete_static_state(self.CONTEXT_ANSWERER_USER_ID)
        context.delete_static_state(self.CONTEXT_ANSWERER_NAME)
        context.delete_static_state(self.CONTEXT_ANSWER_RECEIVED)
        context.delete_static_state(self.CONTEXT_TASK_ID)
        context.delete_static_state(self.CONTEXT_TRANSACTION_ID)
        context.delete_static_state(self.CONTEXT_QUESTIONER_USER_ID)
        context.delete_static_state(self.CONTEXT_QUESTION_ANSWERED)
        context.delete_static_state(self.CONTEXT_CURRENT_STATE)

        if intent == self.INTENT_SHARE_DETAILS:
            message = self._translator.get_translation_instance(user_locale).with_text("sharing_details_message").with_substitution("answerer", answerer_name).translate()
            message = TextualResponse(message)

            user_accounts = self.get_user_accounts(answerer_user_id)
            if len(user_accounts) != 1:
                logger.error(f"No context associated with WeNet user {answerer_user_id}")
                raise ValueError(f"No context associated with WeNet user {answerer_user_id}")
            answerer_account = user_accounts[0]
            blocked_users_for_contact_request = answerer_account.context.get_static_state(self.CONTEXT_BLOCKED_USERS_FOR_CONTACT_REQUEST, [])
            if questioner_user_id not in blocked_users_for_contact_request:
                answerer_locale = self._get_user_locale_from_wenet_id(answerer_user_id, context=answerer_account.context)
                service_api = self._get_service_api_interface_connector_from_context(context)
                questioner = service_api.get_user_profile(questioner_user_id)
                task = service_api.get_task(task_id)
                questioner_name = questioner.name.first if questioner.name.first and not task.attributes.get("anonymous", False) else self._translator.get_translation_instance(answerer_locale).with_text("anonymous_user").translate()

                notification_message = self._translator.get_translation_instance(answerer_locale).with_text("share_details_to_questioner") \
                    .with_substitution("questioner", questioner_name) \
                    .with_substitution("question", question) \
                    .with_substitution("answer", answer) \
                    .translate()
                notification_message = TelegramRapidAnswerResponse(TextualResponse(notification_message), row_displacement=[1, 1, 1])
                button_share_details = self._translator.get_translation_instance(answerer_locale).with_text("share_details").translate()
                button_not_share_details = self._translator.get_translation_instance(answerer_locale).with_text("not_now_share_details").translate()
                button_block_share_details = self._translator.get_translation_instance(answerer_locale).with_text("block_share_details").translate()
                button_ids = [str(uuid.uuid4()) for _ in range(3)]
                button_data = {
                    "answerer_user_id": answerer_user_id,
                    "answerer_name": answerer_name,
                    "transaction_id": transaction_id,
                    "task_id": task_id,
                    "questioner_user_id": questioner_user_id,
                    "questioner_name": questioner_name,
                    "related_buttons": button_ids
                }
                self.cache.cache(ButtonPayload(button_data, self.INTENT_SHARE_DETAILS_TO_QUESTIONER).to_repr(), key=button_ids[0])
                notification_message.with_textual_option(button_share_details, self.INTENT_BUTTON_WITH_PAYLOAD.format(button_ids[0]))
                self.cache.cache(ButtonPayload(button_data, self.INTENT_NOT_NOW_SHARE_DETAILS).to_repr(), key=button_ids[1])
                notification_message.with_textual_option(button_not_share_details, self.INTENT_BUTTON_WITH_PAYLOAD.format(button_ids[1]))
                self.cache.cache(ButtonPayload(button_data, self.INTENT_BLOCK_SHARE_DETAILS).to_repr(), key=button_ids[2])
                notification_message.with_textual_option(button_block_share_details, self.INTENT_BUTTON_WITH_PAYLOAD.format(button_ids[2]))

                answerer_service_api = self._get_service_api_interface_connector_from_context(answerer_account.context)
                notification = self._get_notification_event_based_on_what_user_is_doing(answerer_account.context, answerer_account.social_details, [notification_message], incoming_event.incoming_message.message_id)
                try:
                    self.send_notification(notification)
                    for outgoing_message in notification.messages:
                        try:
                            answerer_service_api.log_message(self.message_parser_for_logs.create_response(outgoing_message, answerer_account.context.get_static_state(self.CONTEXT_WENET_USER_ID), incoming_event.incoming_message.message_id))
                        except TypeError as e:
                            logger.warning("Unsupported message to log", exc_info=e)
                        except CreationError:
                            logger.warning("Unable to send logs to the service API")

                    if notification.context is not None:
                        self._interface_connector.update_user_context(UserConversationContext(
                            social_details=notification.social_details,
                            context=notification.context,
                            version=UserConversationContext.VERSION_V3)
                        )
                except Exception as e:
                    logger.exception(f"An exception [{type(e)}] occurs sending the notification [{notification.to_repr()}]", exc_info=e)

        else:
            message = self._translator.get_translation_instance(user_locale).with_text("not_sharing_details_message").with_substitution("answerer", answerer_name).translate()
            message = TextualResponse(message)

        response.with_message(message)
        response.with_context(context)
        return response

    def action_follow_up_2(self, incoming_event: IncomingSocialEvent, button_payload: ButtonPayload) -> OutgoingEvent:
        response = OutgoingEvent(social_details=incoming_event.social_details)
        user_locale = self._get_user_locale_from_incoming_event(incoming_event)

        context = incoming_event.context
        answerer_contact = self._get_telegram_user(context)
        if answerer_contact:
            answerer_user_id = button_payload.payload["answerer_user_id"]
            answerer_name = button_payload.payload["answerer_name"]
            questioner_user_id = button_payload.payload["questioner_user_id"]
            questioner_name = button_payload.payload["questioner_name"]
            task_id = button_payload.payload["task_id"]
            transaction_id = button_payload.payload["transaction_id"]
            user_accounts = self.get_user_accounts(questioner_user_id)
            if len(user_accounts) != 1:
                logger.error(f"No context associated with WeNet user {questioner_user_id}")
                raise ValueError(f"No context associated with WeNet user {questioner_user_id}")
            questioner_account = user_accounts[0]
            questioner_locale = self._get_user_locale_from_wenet_id(questioner_user_id, context=questioner_account.context)
            questioner_contact = self._get_telegram_user(questioner_account.context)

            if questioner_contact:
                message = self._translator.get_translation_instance(user_locale).with_text("share_questioner_contact") \
                    .with_substitution("questioner_name", questioner_name) \
                    .with_substitution("questioner_contact", questioner_contact) \
                    .translate() + "\n\n" + self._translator.get_translation_instance(user_locale).with_text("shared_answerer_contact") \
                    .with_substitution("questioner_name", questioner_name) \
                    .translate()

                notification_message = self._translator.get_translation_instance(questioner_locale).with_text("share_answerer_contact") \
                    .with_substitution("answerer_name", answerer_name) \
                    .with_substitution("answerer_contact", answerer_contact) \
                    .translate() + "\n\n" + self._translator.get_translation_instance(questioner_locale).with_text("shared_questioner_contact") \
                    .with_substitution("answerer_name", answerer_name) \
                    .translate()

            else:  # Handle cases in which answerer username is not available, since he can remove it, saying that it is not possible to share it
                message = self._translator.get_translation_instance(user_locale).with_text("no_contact_available") \
                              .with_substitution("questioner_name", questioner_name) \
                              .with_substitution("questioner_contact", questioner_contact) \
                              .translate() + "\n\n" + self._translator.get_translation_instance(user_locale).with_text("shared_answerer_contact") \
                              .with_substitution("questioner_name", questioner_name) \
                              .translate()

                notification_message = self._translator.get_translation_instance(questioner_locale).with_text("share_answerer_contact") \
                                           .with_substitution("answerer_name", answerer_name) \
                                           .with_substitution("answerer_contact", answerer_contact) \
                                           .translate() + "\n\n" + self._translator.get_translation_instance(questioner_locale).with_text("not_shared_contact") \
                                           .with_substitution("answerer_name", answerer_name) \
                                           .translate()

            message = TextualResponse(message)
            notification_message = TextualResponse(notification_message)

            # Store the follow-up event in a transaction
            service_api = self._get_service_api_interface_connector_from_context(context)
            try:
                transaction = TaskTransaction(None, task_id, self.LABEL_FOLLOW_UP_TRANSACTION, int(datetime.now().timestamp()), int(datetime.now().timestamp()), answerer_user_id, {
                    "transactionId": transaction_id
                }, [])
                service_api.create_task_transaction(transaction)
                logger.info("Sent task transaction: %s" % str(transaction.to_repr()))
            except CreationError as e:
                logger.error(
                    "Error in the creation of the transaction to like the answer for the question [%s]. The service API responded with code %d and message %s"
                    % (task_id, e.http_status_code, json.dumps(e.server_response))
                )

            questioner_service_api = self._get_service_api_interface_connector_from_context(questioner_account.context)
            notification = self._get_notification_event_based_on_what_user_is_doing(questioner_account.context, questioner_account.social_details, [notification_message], incoming_event.incoming_message.message_id)
            try:
                self.send_notification(notification)
                for outgoing_message in notification.messages:
                    try:
                        questioner_service_api.log_message(self.message_parser_for_logs.create_response(outgoing_message, questioner_account.context.get_static_state(self.CONTEXT_WENET_USER_ID), incoming_event.incoming_message.message_id))
                    except TypeError as e:
                        logger.warning("Unsupported message to log", exc_info=e)
                    except CreationError:
                        logger.warning("Unable to send logs to the service API")

                if notification.context is not None:
                    self._interface_connector.update_user_context(UserConversationContext(
                        social_details=notification.social_details,
                        context=notification.context,
                        version=UserConversationContext.VERSION_V3)
                    )
            except Exception as e:
                logger.exception(f"An exception [{type(e)}] occurs sending the notification [{notification.to_repr()}]", exc_info=e)

        else:  # if there is no username on Telegram when he wants to share it: ask to set username sending to him the telegram instruction in order to set it
            message = self._translator.get_translation_instance(user_locale).with_text("set_telegram_username").translate()
            message = TelegramRapidAnswerResponse(TextualResponse(message), row_displacement=[1])
            button_share_details = self._translator.get_translation_instance(user_locale).with_text("share_details").translate()
            button_id = str(uuid.uuid4())
            self.cache.cache(ButtonPayload(button_payload.payload, self.INTENT_SHARE_DETAILS_TO_QUESTIONER).to_repr(), key=button_id)
            message.with_textual_option(button_share_details, self.INTENT_BUTTON_WITH_PAYLOAD.format(button_id))

        response.with_message(message)
        response.with_context(context)
        return response

    def action_not_follow_up(self, incoming_event: IncomingSocialEvent, button_payload: ButtonPayload) -> OutgoingEvent:
        response = OutgoingEvent(social_details=incoming_event.social_details)
        user_locale = self._get_user_locale_from_incoming_event(incoming_event)

        context = incoming_event.context
        answerer_name = button_payload.payload["answerer_name"]
        questioner_user_id = button_payload.payload["questioner_user_id"]
        questioner_name = button_payload.payload["questioner_name"]

        user_accounts = self.get_user_accounts(questioner_user_id)
        if len(user_accounts) != 1:
            logger.error(f"No context associated with WeNet user {questioner_user_id}")
            raise ValueError(f"No context associated with WeNet user {questioner_user_id}")
        questioner_account = user_accounts[0]
        questioner_locale = self._get_user_locale_from_wenet_id(questioner_user_id, context=questioner_account.context)

        message = self._translator.get_translation_instance(user_locale).with_text("not_follow_up") \
            .with_substitution("questioner_name", questioner_name) \
            .translate()
        message = TextualResponse(message)

        notification_message = self._translator.get_translation_instance(questioner_locale).with_text("not_share_answerer_contact") \
            .with_substitution("answerer_name", answerer_name) \
            .translate()
        notification_message = TextualResponse(notification_message)

        questioner_service_api = self._get_service_api_interface_connector_from_context(questioner_account.context)
        notification = self._get_notification_event_based_on_what_user_is_doing(questioner_account.context, questioner_account.social_details, [notification_message], incoming_event.incoming_message.message_id)
        try:
            self.send_notification(notification)
            for outgoing_message in notification.messages:
                try:
                    questioner_service_api.log_message(self.message_parser_for_logs.create_response(outgoing_message, questioner_account.context.get_static_state(self.CONTEXT_WENET_USER_ID), incoming_event.incoming_message.message_id))
                except TypeError as e:
                    logger.warning("Unsupported message to log", exc_info=e)
                except CreationError:
                    logger.warning("Unable to send logs to the service API")

            if notification.context is not None:
                self._interface_connector.update_user_context(UserConversationContext(
                    social_details=notification.social_details,
                    context=notification.context,
                    version=UserConversationContext.VERSION_V3)
                )
        except Exception as e:
            logger.exception(f"An exception [{type(e)}] occurs sending the notification [{notification.to_repr()}]", exc_info=e)

        response.with_message(message)
        response.with_context(context)
        return response

    def action_block_follow_up(self, incoming_event: IncomingSocialEvent, button_payload: ButtonPayload) -> OutgoingEvent:
        response = OutgoingEvent(social_details=incoming_event.social_details)
        user_locale = self._get_user_locale_from_incoming_event(incoming_event)

        context = incoming_event.context
        message = self._translator.get_translation_instance(user_locale).with_text("block_follow_up").translate()
        message = TextualResponse(message)

        # Store in the context of the user that he does not want messages from that user
        questioner_user_id = button_payload.payload["questioner_user_id"]
        blocked_users_for_contact_request = context.get_static_state(self.CONTEXT_BLOCKED_USERS_FOR_CONTACT_REQUEST, [])
        blocked_users_for_contact_request.append(questioner_user_id)
        context.with_static_state(self.CONTEXT_BLOCKED_USERS_FOR_CONTACT_REQUEST, blocked_users_for_contact_request)

        response.with_message(message)
        response.with_context(context)
        return response

    def action_like_answer(self, incoming_event: IncomingSocialEvent, button_payload: ButtonPayload) -> OutgoingEvent:
        response = OutgoingEvent(social_details=incoming_event.social_details)
        user_locale = self._get_user_locale_from_incoming_event(incoming_event)
        context = incoming_event.context
        if context is not None:
            service_api = self._get_service_api_interface_connector_from_context(incoming_event.context)
        else:
            raise Exception(f"Missing conversation context for event {incoming_event}")

        task_id = button_payload.payload["task_id"]
        actioneer_id = context.get_static_state(self.CONTEXT_WENET_USER_ID)
        try:
            transaction = TaskTransaction(None, task_id, self.LABEL_LIKE_ANSWER_TRANSACTION, int(datetime.now().timestamp()), int(datetime.now().timestamp()), actioneer_id, {
                "transactionId": button_payload.payload["transaction_id"]
            }, [])
            service_api.create_task_transaction(transaction)
            logger.info("Sent task transaction: %s" % str(transaction.to_repr()))
            message = self._translator.get_translation_instance(user_locale).with_text("like_answer_text").translate()
            response.with_message(TextualResponse(message))
        except CreationError as e:
            response.with_message(TextualResponse(self._translator.get_translation_instance(user_locale).with_text("error_task_creation").translate()))
            logger.error(
                "Error in the creation of the transaction to like the answer for the question [%s]. The service API responded with code %d and message %s"
                % (task_id, e.http_status_code, json.dumps(e.server_response))
            )

        user_accounts = self.get_user_accounts(button_payload.payload["answerer_user_id"])
        if len(user_accounts) != 1:
            logger.error(f"No context associated with WeNet user {button_payload.payload['answerer_user_id']}")
            raise ValueError(f"No context associated with WeNet user {button_payload.payload['answerer_user_id']}")
        answerer_account = user_accounts[0]
        answerer_locale = self._get_user_locale_from_wenet_id(button_payload.payload["answerer_user_id"], context=answerer_account.context)

        task = service_api.get_task(task_id)
        questioner = service_api.get_user_profile(actioneer_id)
        questioner_name = questioner.name.first if questioner.name.first and not task.attributes.get("anonymous", False) else self._translator.get_translation_instance(answerer_locale).with_text("anonymous_user").translate()

        notification_message = self._translator.get_translation_instance(answerer_locale).with_text("liked_answer") \
            .with_substitution("questioner_name", questioner_name) \
            .translate()
        notification_message = TextualResponse(notification_message)

        answerer_service_api = self._get_service_api_interface_connector_from_context(answerer_account.context)
        notification = self._get_notification_event_based_on_what_user_is_doing(answerer_account.context, answerer_account.social_details, [notification_message], incoming_event.incoming_message.message_id)
        try:
            self.send_notification(notification)
            for outgoing_message in notification.messages:
                try:
                    answerer_service_api.log_message(self.message_parser_for_logs.create_response(outgoing_message, answerer_account.context.get_static_state(self.CONTEXT_WENET_USER_ID), incoming_event.incoming_message.message_id))
                except TypeError as e:
                    logger.warning("Unsupported message to log", exc_info=e)
                except CreationError:
                    logger.warning("Unable to send logs to the service API")

            if notification.context is not None:
                self._interface_connector.update_user_context(UserConversationContext(
                    social_details=notification.social_details,
                    context=notification.context,
                    version=UserConversationContext.VERSION_V3)
                )
        except Exception as e:
            logger.exception(f"An exception [{type(e)}] occurs sending the notification [{notification.to_repr()}]", exc_info=e)

        response.with_context(context)
        return response

    def action_best_answer_0(self, incoming_event: IncomingSocialEvent, button_payload: ButtonPayload) -> OutgoingEvent:
        response = OutgoingEvent(social_details=incoming_event.social_details)
        user_locale = self._get_user_locale_from_incoming_event(incoming_event)
        context = incoming_event.context
        context.with_static_state(self.CONTEXT_TASK_ID, button_payload.payload["task_id"])
        context.with_static_state(self.CONTEXT_TRANSACTION_ID, button_payload.payload["transaction_id"])
        context.with_static_state(self.CONTEXT_CURRENT_STATE, self.STATE_BEST_ANSWER_0)

        message = self._translator.get_translation_instance(user_locale).with_text("best_answer_0").translate()
        button_1_text = self._translator.get_translation_instance(user_locale).with_text("answer_reason_funny").translate()
        button_2_text = self._translator.get_translation_instance(user_locale).with_text("answer_reason_thoughtful").translate()
        button_3_text = self._translator.get_translation_instance(user_locale).with_text("answer_reason_informative").translate()
        button_4_text = self._translator.get_translation_instance(user_locale).with_text("answer_reason_creative").translate()
        button_5_text = self._translator.get_translation_instance(user_locale).with_text("answer_reason_honest").translate()
        button_6_text = self._translator.get_translation_instance(user_locale).with_text("answer_reason_kind").translate()
        button_7_text = self._translator.get_translation_instance(user_locale).with_text("answer_reason_personal").translate()
        response_with_buttons = TelegramRapidAnswerResponse(TextualResponse(message), row_displacement=[2, 2, 2, 1])
        response_with_buttons.with_textual_option(button_1_text, self.INTENT_CHOSEN_ANSWER_FUNNY)
        response_with_buttons.with_textual_option(button_2_text, self.INTENT_CHOSEN_ANSWER_THOUGHTFUL)
        response_with_buttons.with_textual_option(button_3_text, self.INTENT_CHOSEN_ANSWER_INFORMATIVE)
        response_with_buttons.with_textual_option(button_4_text, self.INTENT_CHOSEN_ANSWER_CREATIVE)
        response_with_buttons.with_textual_option(button_5_text, self.INTENT_CHOSEN_ANSWER_HONEST)
        response_with_buttons.with_textual_option(button_6_text, self.INTENT_CHOSEN_ANSWER_KIND)
        response_with_buttons.with_textual_option(button_7_text, self.INTENT_CHOSEN_ANSWER_PERSONAL)
        response.with_message(response_with_buttons)
        response.with_context(context)
        return response

    def action_best_answer_publish(self, incoming_event: IncomingSocialEvent, intent: str) -> OutgoingEvent:
        user_locale = self._get_user_locale_from_incoming_event(incoming_event)
        response = OutgoingEvent(social_details=incoming_event.social_details)
        context = incoming_event.context
        if context is not None:
            service_api = self._get_service_api_interface_connector_from_context(context)
        else:
            raise Exception(f"Missing conversation context for event {incoming_event}")

        task_id = context.get_static_state(self.CONTEXT_TASK_ID)
        questioner_name = context.get_static_state(self.CONTEXT_QUESTIONER_NAME)
        question_text = context.get_static_state(self.CONTEXT_QUESTION)
        best_answer_transaction = context.get_static_state(self.CONTEXT_TRANSACTION_ID)
        context.delete_static_state(self.CONTEXT_TASK_ID)
        context.delete_static_state(self.CONTEXT_TRANSACTION_ID)
        context.delete_static_state(self.CONTEXT_QUESTIONER_NAME)
        context.delete_static_state(self.CONTEXT_QUESTION)
        context.delete_static_state(self.CONTEXT_CURRENT_STATE)

        transaction_ids = []
        message_answers = []
        message_users = []
        task = service_api.get_task(task_id)
        for transaction in task.transactions:
            if transaction.label == self.LABEL_ANSWER_TRANSACTION and transaction.attributes.get("publish"):
                message_answers.append(self.parse_text_with_markdown(self._prepare_string_to_telegram(transaction.attributes["answer"])))
                answerer_user = service_api.get_user_profile(transaction.actioneer_id)
                answerer = self._translator.get_translation_instance(self.publication_language).with_text("anonymous_user").translate() if transaction.attributes.get("publishAnonymously") or not answerer_user.name.first else answerer_user.name.first
                message_users.append(answerer)
                transaction_ids.append(transaction.id)
        message_attributes = self._translator.get_translation_instance(self.publication_language) \
            .with_text("asked_message_without_attributes_user") \
            .with_substitution("user", questioner_name) \
            .with_substitution("question", question_text) \
            .translate()

        message_upper_part = f"{message_attributes} \n\n"
        message_notification = []
        if len(message_answers) != 0:
            message_upper_part += f"{self._translator.get_translation_instance(self.publication_language).with_text('collected_answers').translate()} \n\n"
            message_notification.append(TextualResponse(message_upper_part))
            message_string = ""

            message_best_answer = self._translator.get_translation_instance(self.publication_language)\
                .with_text('chosen_answer_by_user')\
                .with_substitution("user", questioner_name).translate()

            n = 5  # group of answers to show on one batch of result
            output = []
            for i in range(len(message_answers)):
                answer_string = f"{i + 1}. {message_answers[i]} - {message_users[i]}"
                if transaction_ids[i] == best_answer_transaction:
                    answer_string += " " + message_best_answer + "\n"
                else:
                    answer_string += "\n"
                output.append(answer_string)
            grouped_answers = [output[i:i + n] for i in range(0, len(output), n)]

            for i in range(len(grouped_answers)):
                message_string_middle = ""
                if i != len(grouped_answers) - 1:
                    for j in range(len(grouped_answers[i])):
                        message_string_middle += grouped_answers[i][j]
                    answer_middle_part = TextualResponse(message_string_middle)
                    message_notification.append(answer_middle_part)
                else:
                    for j in range(len(grouped_answers[i])):
                        message_string += grouped_answers[i][j]

            if best_answer_transaction not in transaction_ids:
                message_string += f"\n\n {self._translator.get_translation_instance(self.publication_language).with_text('best_answer_not_published').translate()} \n\n"
            message_notification.append(TextualResponse(message_string))
        else:
            message_upper_part += f"{self._translator.get_translation_instance(self.publication_language).with_text('no_collected_answers').translate()} \n\n"
            message_notification.append(TextualResponse(message_upper_part))

        if intent == self.INTENT_PUBLISH and isinstance(incoming_event.social_details, TelegramDetails):
            notification = NotificationEvent(social_details=TelegramDetails(None, self.channel_id, incoming_event.social_details.telegram_bot_id), messages=message_notification)
            try:
                self.send_notification(notification)
                logger.info(f"Notification sent to the telegram channel {self.channel_id}")
            except Exception as e:
                logger.exception(f"An exception [{type(e)}] occurs sending the notification [{notification.to_repr()}]", exc_info=e)

        message = self._translator.get_translation_instance(user_locale).with_text("thank_you_message").translate()
        response.with_message(TextualResponse(message))
        response.with_context(context)
        return response

    def action_best_answer_1(self, incoming_event: IncomingSocialEvent, intent: str) -> OutgoingEvent:
        user_locale = self._get_user_locale_from_incoming_event(incoming_event)
        response = OutgoingEvent(social_details=incoming_event.social_details)
        context = incoming_event.context
        context.with_static_state(self.CONTEXT_CURRENT_STATE, self.STATE_BEST_ANSWER_1)
        context.with_static_state(self.CONTEXT_CHOSEN_ANSWER_REASON, intent)
        message = self._translator.get_translation_instance(user_locale).with_text("best_answer_helpful").translate()
        button_1_text = self._translator.get_translation_instance(user_locale).with_text("not_at_all_helpful").translate()
        button_2_text = self._translator.get_translation_instance(user_locale).with_text("slightly_helpful").translate()
        button_3_text = self._translator.get_translation_instance(user_locale).with_text("somewhat_helpful").translate()
        button_4_text = self._translator.get_translation_instance(user_locale).with_text("very_helpful").translate()
        button_5_text = self._translator.get_translation_instance(user_locale).with_text("extremely_helpful").translate()
        response_with_buttons = TelegramRapidAnswerResponse(TextualResponse(message), row_displacement=[2, 2, 1])
        response_with_buttons.with_textual_option(button_1_text, self.INTENT_NOT_AT_ALL_HELPFUL)
        response_with_buttons.with_textual_option(button_2_text, self.INTENT_SLIGHTLY_HELPFUL)
        response_with_buttons.with_textual_option(button_3_text, self.INTENT_SOMEWHAT_HELPFUL)
        response_with_buttons.with_textual_option(button_4_text, self.INTENT_VERY_HELPFUL)
        response_with_buttons.with_textual_option(button_5_text, self.INTENT_EXTREMELY_HELPFUL)
        response.with_message(response_with_buttons)
        response.with_context(context)
        return response

    def action_best_answer_2(self, incoming_event: IncomingSocialEvent, intent: str) -> OutgoingEvent:
        response = OutgoingEvent(social_details=incoming_event.social_details)
        user_locale = self._get_user_locale_from_incoming_event(incoming_event)
        context = incoming_event.context
        if context is not None:
            service_api = self._get_service_api_interface_connector_from_context(context)
        else:
            raise Exception(f"Missing conversation context for event {incoming_event}")

        if not context.has_static_state(self.CONTEXT_TASK_ID) \
                or not context.has_static_state(self.CONTEXT_TRANSACTION_ID) \
                or not context.has_static_state(self.CONTEXT_CHOSEN_ANSWER_REASON):
            logger.error(f"Expected {self.CONTEXT_TASK_ID}, {self.CONTEXT_TRANSACTION_ID} "
                         f"and {self.CONTEXT_CHOSEN_ANSWER_REASON} in the context")
            raise Exception(f"Expected {self.CONTEXT_TASK_ID}, {self.CONTEXT_TRANSACTION_ID}, "
                            f"and {self.CONTEXT_CHOSEN_ANSWER_REASON} in the context")
        task_id = context.get_static_state(self.CONTEXT_TASK_ID)
        transaction_id = context.get_static_state(self.CONTEXT_TRANSACTION_ID)
        reason = context.get_static_state(self.CONTEXT_CHOSEN_ANSWER_REASON)
        attributes = {
            "transactionId": transaction_id,
            "reason": reason,
            "helpful": intent
        }
        actioneer_id = incoming_event.context.get_static_state(self.CONTEXT_WENET_USER_ID)
        try:
            transaction = TaskTransaction(None, task_id, self.LABEL_BEST_ANSWER_TRANSACTION, int(datetime.now().timestamp()), int(datetime.now().timestamp()), actioneer_id, attributes, [])
            service_api.create_task_transaction(transaction)
            logger.info("Sent task transaction: %s" % str(transaction.to_repr()))
            message = self._translator.get_translation_instance(user_locale).with_text("best_answer_final_message").translate()
            response.with_message(TextualResponse(message))
        except CreationError as e:
            response.with_message(TextualResponse(self._translator.get_translation_instance(user_locale).with_text("error_task_creation").translate()))
            logger.error(
                "Error in the creation of the transaction for reporting the task [%s]. The service API responded with code %d and message %s"
                % (task_id, e.http_status_code, json.dumps(e.server_response))
            )
        finally:
            context.delete_static_state(self.CONTEXT_TASK_ID)
            context.delete_static_state(self.CONTEXT_TRANSACTION_ID)
            context.delete_static_state(self.CONTEXT_CHOSEN_ANSWER_REASON)
            context.delete_static_state(self.CONTEXT_QUESTIONER_NAME)
            context.delete_static_state(self.CONTEXT_QUESTION)
            context.delete_static_state(self.CONTEXT_BEST_ANSWER)
            context.delete_static_state(self.CONTEXT_ANSWERER_NAME)
            context.delete_static_state(self.CONTEXT_CURRENT_STATE)

        if self.channel_id:  # ask to publish only if there is the channel
            task = service_api.get_task(task_id)
            question = self.parse_text_with_markdown(self._prepare_string_to_telegram(task.goal.name))
            anonymous = task.attributes.get("anonymous", False)
            questioning_user = None
            if not anonymous:
                questioning_user = service_api.get_user_profile(str(task.requester_id))
            context.with_static_state(self.CONTEXT_CURRENT_STATE, self.STATE_BEST_ANSWER_PUBLISH)
            context.with_static_state(self.CONTEXT_QUESTIONER_NAME, questioning_user.name.first if not anonymous and questioning_user and questioning_user.name.first else self._translator.get_translation_instance(self.publication_language).with_text("anonymous_user").translate())
            context.with_static_state(self.CONTEXT_QUESTION, question)
            context.with_static_state(self.CONTEXT_TASK_ID, task_id)
            context.with_static_state(self.CONTEXT_TRANSACTION_ID, transaction_id)
            message = self._translator.get_translation_instance(user_locale).with_text("publish_question_to_channel").translate()
            button_1_text = self._translator.get_translation_instance(user_locale).with_text("publish").translate()
            button_2_text = self._translator.get_translation_instance(user_locale).with_text("not_publish").translate()
            message = TelegramRapidAnswerResponse(TextualResponse(message), row_displacement=[2])
            message.with_textual_option(button_1_text, self.INTENT_PUBLISH)
            message.with_textual_option(button_2_text, self.INTENT_NOT_PUBLISH)
            response.with_message(message)

        response.with_context(context)
        return response

    def _get_eligible_tasks(self, service_api: ServiceApiInterface, user_id: str, current_date: int) -> List[Task]:
        """
        From all tasks, pick the ones that are:
            - task owner is not answering
            - task owner is not answering their own question
            - tasks are within the expiration date
            - task owner is requested to ask more questions
        """
        eligible_tasks = []
        for task in service_api.get_all_tasks(app_id=self.app_id, task_type_id=self.task_type_id, has_close_ts=False):
            if task.requester_id != user_id and user_id not in set([transaction.actioneer_id for transaction in task.transactions if transaction.label == self.LABEL_ANSWER_TRANSACTION]):
                if task.attributes.get("expirationDate") < current_date:
                    for transaction in task.transactions:
                        if transaction.label == self.LABEL_MORE_ANSWER_TRANSACTION:
                            if transaction.attributes.get("expirationDate") > current_date:
                                eligible_tasks.append(task)
                                break
                else:
                    eligible_tasks.append(task)
        return eligible_tasks

    def action_answer(self, incoming_event: IncomingSocialEvent, _: str) -> OutgoingEvent:
        response = OutgoingEvent(social_details=incoming_event.social_details)
        user_locale = self._get_user_locale_from_incoming_event(incoming_event)
        context = incoming_event.context
        if context is not None:
            service_api = self._get_service_api_interface_connector_from_context(incoming_event.context)
        else:
            raise Exception(f"Missing conversation context for event {incoming_event}")
        user_id = context.get_static_state(self.CONTEXT_WENET_USER_ID)
        current_date = int(datetime.now().timestamp())
        eligible_tasks = self._get_eligible_tasks(service_api, user_id, current_date)

        if not eligible_tasks:
            response.with_message(TextualResponse(
                self._translator.get_translation_instance(user_locale).with_text("answers_no_tasks").translate())
            )
        else:
            if len(eligible_tasks) > 3:
                # if more than 3 tasks, pick 3 random
                eligible_tasks = random.sample(eligible_tasks, k=3)
            text = self._translator.get_translation_instance(user_locale).with_text("answers_tasks_intro").translate()
            proposed_tasks = []
            tasks_texts = []
            for task in eligible_tasks:
                questioning_user = service_api.get_user_profile(str(task.requester_id))
                if questioning_user:
                    task_text = f"#{1 + len(proposed_tasks)}: *{self.parse_text_with_markdown(self._prepare_string_to_telegram(task.goal.name))}* - {questioning_user.name.first if questioning_user.name.first and not task.attributes.get('anonymous') else self._translator.get_translation_instance(user_locale).with_text('anonymous_user').translate()}"
                    if task.attributes.get("domain") == self.INTENT_SENSITIVE_QUESTION:
                        task_text = task_text + f" - {self._translator.get_translation_instance(user_locale).with_text('sensitive').translate()}"
                    tasks_texts.append(task_text)
                    proposed_tasks.append(task)
            message_text = "\n".join([text] + tasks_texts + [self._translator.get_translation_instance(user_locale).with_text("answers_tasks_choose").translate()])
            rapid_answer = TelegramRapidAnswerResponse(TextualResponse(message_text))
            for i in range(len(proposed_tasks)):
                button_id = self.cache.cache(ButtonPayload({"task_id": proposed_tasks[i].task_id, "sensitive": proposed_tasks[i].attributes.get("domain") == self.INTENT_SENSITIVE_QUESTION}, self.INTENT_ANSWER_PICKED_QUESTION).to_repr())
                rapid_answer.with_textual_option(f"#{1 + i}", self.INTENT_BUTTON_WITH_PAYLOAD.format(button_id))
            response.with_message(rapid_answer)
        response.with_context(context)
        return response

    def action_badges(self, incoming_event: IncomingSocialEvent, _: str) -> OutgoingEvent:
        user_locale = self._get_user_locale_from_incoming_event(incoming_event)
        response = OutgoingEvent(incoming_event.social_details)
        badges_message = self._translator.get_translation_instance(user_locale).with_text("badges") \
            .with_substitution("base_url", self.wenet_hub_url) \
            .with_substitution("app_id", self.app_id) \
            .translate()
        response.with_message(TextualResponse(badges_message))
        return response

    # def action_profile(self, incoming_event: IncomingSocialEvent, _: str) -> OutgoingEvent:
    #     user_locale = self._get_user_locale_from_incoming_event(incoming_event)
    #     response = OutgoingEvent(incoming_event.social_details)
    #     text = self._translator.get_translation_instance(user_locale).with_text("not_implemented").translate()
    #     response.with_message(TextualResponse(text))
    #     return response
