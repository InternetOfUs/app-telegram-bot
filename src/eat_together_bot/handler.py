import json
import logging
from datetime import datetime, timedelta
from typing import Optional, List
from uuid import uuid4

from emoji import emojize

from chatbot_core.model.context import ConversationContext
from chatbot_core.model.details import TelegramDetails
from chatbot_core.model.event import IncomingSocialEvent
from chatbot_core.model.message import IncomingTextMessage, IncomingTelegramCarouselCommand, IncomingCommand
from chatbot_core.model.user_context import UserConversationContext
from chatbot_core.nlp.handler import NLPHandler
from chatbot_core.translator.translator import Translator
from chatbot_core.v3.connector.social_connector import SocialConnector
from chatbot_core.v3.connector.social_connectors.telegram_connector import TelegramSocialConnector
from chatbot_core.v3.handler.helpers.intent_manager import IntentFulfillerV3
from chatbot_core.v3.logger.event_logger import LoggerConnector
from chatbot_core.v3.model.actions import TelegramCallbackButton
from chatbot_core.v3.model.messages import TextualResponse, RapidAnswerResponse, TelegramTextualResponse, \
    TelegramRapidAnswerResponse, TelegramCarouselResponse
from chatbot_core.v3.model.outgoing_event import OutgoingEvent, NotificationEvent
from common.utils import Utils
from common.wenet_event_handler import WenetEventHandler
from uhopper.utils.alert.module import AlertModule
from wenet.interface.exceptions import CreationError, RefreshTokenExpiredError
from wenet.model.callback_message.event import WeNetAuthenticationEvent
from wenet.model.callback_message.message import TextualMessage, \
    TaskProposalNotification, TaskVolunteerNotification, TaskSelectionNotification, Message, TaskConcludedNotification
from wenet.model.task.task import Task, TaskGoal
from wenet.model.task.transaction import TaskTransaction

logger = logging.getLogger("uhopper.chatbot.wenet.eattogether.chatbot")


class EatTogetherHandler(WenetEventHandler):
    # context keys
    CONTEXT_ORGANIZE_TASK_OBJECT = 'organize_task_object'
    CONTEXT_PROPOSAL_TASK_DICT = 'proposal_task_dict'
    CONTEXT_VOLUNTEER_CANDIDATURE_DICT = 'volunteer_candidature_dict'
    CONTEXT_USER_TASK_LIST = 'task_list'
    CONTEXT_USER_TASK_INDEX = 'task_index'
    CONTEXT_USER_TASK_ACTION = 'task_action'
    TASK_ACTION_CONCLUDE = 'conclude'
    # all the recognize intents
    INTENT_ORGANIZE = '/organize'
    INTENT_CONFIRM_TASK_CREATION = 'task_creation_confirm'
    INTENT_CANCEL_TASK_CREATION = 'task_creation_cancel'
    INTENT_CONFIRM_TASK_PROPOSAL = 'task-cr-conf_{}'
    INTENT_CANCEL_TASK_PROPOSAL = 'task-cr-can_{}'
    INTENT_VOLUNTEER_INFO = 'vol-info_{}'
    INTENT_CREATOR_INFO = 'creator-info_{}'
    INTENT_CONFIRM_VOLUNTEER_PROPOSAL = 'task-vol-con_{}'
    INTENT_CANCEL_VOLUNTEER_PROPOSAL = 'task-vol-can_{}'
    INTENT_TASK_LIST_PREVIOUS = 'task_list_previous'
    INTENT_TASK_LIST_NEXT = 'task_list_next'
    INTENT_TASK_LIST_CONFIRM = 'task_list_confirm'
    INTENT_TASK_LIST_CANCEL = 'task_list_cancel'
    INTENT_CONCLUDE = '/conclude'
    INTENT_OUTCOME_COMPLETED = 'task_outcome_concluded'
    INTENT_OUTCOME_CANCELLED = 'task_outcome_cancelled'
    INTENT_OUTCOME_FAILED = 'task_outcome_failed'
    # task creation states (/organize command)
    ORGANIZE_Q1 = 'organize_q1'
    ORGANIZE_Q2 = 'organize_q2'
    ORGANIZE_Q3 = 'organize_q3'
    ORGANIZE_Q4 = 'organize_q4'
    ORGANIZE_Q5 = 'organize_q5'
    ORGANIZE_Q6 = 'organize_q6'
    ORGANIZE_RECAP = 'organize_recap'
    # task proposal state
    PROPOSAL = 'send_proposal'
    # volunteer candidature approval state
    VOLUNTEER_CANDIDATURE = 'volunteer_candidature'
    # transaction labels
    LABEL_VOLUNTEER_FOR_TASK = 'volunteerForTask'
    LABEL_REFUSE_TASK = 'refuseTask'
    LABEL_ACCEPT_VOLUNTEER = 'acceptVolunteer'
    LABEL_REFUSE_VOLUNTEER = 'refuseVolunteer'
    LABEL_TASK_COMPLETED = 'taskCompleted'

    def __init__(self, instance_namespace: str,
                 bot_id: str,
                 handler_id: str,
                 telegram_id: str,
                 wenet_instance_url: str,
                 app_id: str,
                 wenet_hub_url: str,
                 task_type_id: str,
                 community_id: str,
                 wenet_authentication_url: str,
                 wenet_authentication_management_url: str,
                 redirect_url: str,
                 client_secret: str,
                 alert_module: AlertModule,
                 connector: SocialConnector,
                 nlp_handler: Optional[NLPHandler],
                 translator: Optional[Translator],
                 delay_between_messages_sec: Optional[int] = None,
                 delay_between_text_sec: Optional[float] = None,
                 logger_connectors: Optional[List[LoggerConnector]] = None):
        """
        Constructor
        :param instance_namespace: instance namespace of the bot
        :param bot_id: id of the bot
        :param handler_id: id of the handler
        :param telegram_id: telegram secret code to communicate with Telegram APIs
        :param wenet_instance_url: wenet instance url (with the protocol - e.g. https)
        :param app_id: WeNet app id with which the bot works
        :param wenet_hub_url: url of the hub, where to redirect not authenticated users
        :param task_type_id: the ID of the type of the tasks the bot will create
        :param alert_module:
        :param connector:
        :param nlp_handler:
        :param translator:
        :param delay_between_messages_sec:
        :param delay_between_text_sec:
        :param logger_connectors:
        """
        super().__init__(instance_namespace, bot_id, handler_id, telegram_id, wenet_instance_url, wenet_hub_url, app_id,
                         client_secret, redirect_url, wenet_authentication_url, wenet_authentication_management_url,
                         task_type_id, community_id, alert_module, connector, nlp_handler, translator,
                         delay_between_messages_sec, delay_between_text_sec, logger_connectors)
        # redirecting the flow in the corresponding points
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3(self.ORGANIZE_Q1, self.organize_q1).with_rule(intent=self.INTENT_ORGANIZE)
        )
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3(self.ORGANIZE_Q2, self.organize_q2).with_rule(
                static_context=(self.CONTEXT_CURRENT_STATE, self.ORGANIZE_Q1))
        )
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3(self.ORGANIZE_Q3, self.organize_q3).with_rule(
                static_context=(self.CONTEXT_CURRENT_STATE, self.ORGANIZE_Q2))
        )
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3(self.ORGANIZE_Q4, self.organize_q4).with_rule(
                static_context=(self.CONTEXT_CURRENT_STATE, self.ORGANIZE_Q3))
        )
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3(self.ORGANIZE_Q5, self.organize_q5).with_rule(
                static_context=(self.CONTEXT_CURRENT_STATE, self.ORGANIZE_Q4))
        )
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3(self.ORGANIZE_Q6, self.organize_q6).with_rule(
                static_context=(self.CONTEXT_CURRENT_STATE, self.ORGANIZE_Q5))
        )
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3(self.ORGANIZE_RECAP, self.organize_recap_message).with_rule(
                static_context=(self.CONTEXT_CURRENT_STATE, self.ORGANIZE_Q6))
        )
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3(self.INTENT_CANCEL_TASK_CREATION, self.action_cancel_task_creation).with_rule(
                intent=self.INTENT_CANCEL_TASK_CREATION,
                static_context=(self.CONTEXT_CURRENT_STATE, self.ORGANIZE_RECAP)
            )
        )
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3(self.INTENT_CONFIRM_TASK_CREATION, self.action_confirm_task_creation).with_rule(
                intent=self.INTENT_CONFIRM_TASK_CREATION,
                static_context=(self.CONTEXT_CURRENT_STATE, self.ORGANIZE_RECAP)
            )
        )
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3(self.INTENT_CONFIRM_TASK_PROPOSAL, self.action_confirm_task_proposal).with_rule(
                regex=self.INTENT_CONFIRM_TASK_PROPOSAL.format("[0-9a-zA-Z]+")
            )
        )
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3(self.INTENT_CANCEL_TASK_PROPOSAL, self.action_delete_task_proposal).with_rule(
                regex=self.INTENT_CANCEL_TASK_PROPOSAL.format("[0-9a-zA-Z]+")
            )
        )
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3(self.INTENT_VOLUNTEER_INFO, self.handle_volunteer_info).with_rule(
                regex=self.INTENT_VOLUNTEER_INFO.format("[0-9a-zA-Z]+")
            )
        )
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3(self.INTENT_CONFIRM_VOLUNTEER_PROPOSAL, self.handle_confirm_candidature).with_rule(
                regex=self.INTENT_CONFIRM_VOLUNTEER_PROPOSAL.format("[0-9a-zA-Z]+")
            )
        )
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3(self.INTENT_CANCEL_VOLUNTEER_PROPOSAL, self.handle_reject_candidature).with_rule(
                regex=self.INTENT_CANCEL_VOLUNTEER_PROPOSAL.format("[0-9a-zA-Z]+")
            )
        )
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3(self.INTENT_CREATOR_INFO, self.get_creator_info).with_rule(
                regex=self.INTENT_CREATOR_INFO.format("[0-9a-zA-Z]+")
            )
        )
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3(self.INTENT_CONCLUDE, self.action_conclude_select_task).with_rule(intent=self.INTENT_CONCLUDE)
        )
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3(self.INTENT_TASK_LIST_CANCEL, self.action_task_conclusion_cancel).with_rule(
                intent=self.INTENT_TASK_LIST_CANCEL, static_context=(self.CONTEXT_CURRENT_STATE, self.TASK_ACTION_CONCLUDE)
            )
        )
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3(self.INTENT_TASK_LIST_CONFIRM, self.action_conclude_task).with_rule(
                intent=self.INTENT_TASK_LIST_CONFIRM, static_context=(self.CONTEXT_CURRENT_STATE, self.TASK_ACTION_CONCLUDE)
            )
        )
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3(self.INTENT_OUTCOME_COMPLETED, self.action_conclude_task_send_transaction).with_rule(
                intent=self.INTENT_OUTCOME_COMPLETED, static_context=(self.CONTEXT_CURRENT_STATE, self.TASK_ACTION_CONCLUDE)
            )
        )
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3(self.INTENT_OUTCOME_CANCELLED, self.action_conclude_task_send_transaction).with_rule(
                intent=self.INTENT_OUTCOME_CANCELLED,
                static_context=(self.CONTEXT_CURRENT_STATE, self.TASK_ACTION_CONCLUDE)
            )
        )
        self.intent_manager.with_fulfiller(
            IntentFulfillerV3(self.INTENT_OUTCOME_FAILED, self.action_conclude_task_send_transaction).with_rule(
                intent=self.INTENT_OUTCOME_FAILED,
                static_context=(self.CONTEXT_CURRENT_STATE, self.TASK_ACTION_CONCLUDE)
            )
        )
        logger.debug("READY")

    def handle_wenet_textual_message(self, message: TextualMessage):  # -> NotificationEvent:
        """
        Handle all the incoming textual messages
        """
        user_accounts = self.get_user_accounts(message.receiver_id)
        if len(user_accounts) != 1:
            logger.error(f"No context associated with Wenet user {message.receiver_id}")
            return

        user_account = user_accounts[0]
        context = user_account.context
        response = TelegramTextualResponse("There is a message for you:\n\n*%s*\n_%s_" % (message.title, message.text))
        return NotificationEvent(user_account.social_details, [response], context)

    def handle_wenet_message(self, message: Message) -> NotificationEvent:
        """
        Handle all the incoming notifications.
        TaskProposal: the bot proposes a user a task to apply
        TaskVolunteer: a volunteer has applied, and the bot asks the creator to reject or confirm the application
        TaskSelection: a volunteer is notified that the owner has (not) approved its application
        """
        user_accounts = self.get_user_accounts(message.receiver_id)
        if len(user_accounts) != 1:
            raise Exception(f"No context associated with Wenet user {message.receiver_id}")

        user_account = user_accounts[0]
        service_api = self._get_service_api_interface_connector_from_context(user_account.context)

        try:
            context = user_account.context
            task = service_api.get_task(str(message.task_id))
            if isinstance(message, TaskProposalNotification):
                # the system wants to propose a task to an user
                try:
                    task_proposals = context.get_static_state(self.CONTEXT_PROPOSAL_TASK_DICT, {})
                    proposal_id = str(uuid4()).replace('-', '')[:20]
                    task_proposals[proposal_id] = {
                        "task": task.to_repr(),
                        "user": message.receiver_id
                    }
                    context.with_static_state(self.CONTEXT_CURRENT_STATE, self.PROPOSAL)
                    context.with_static_state(self.CONTEXT_PROPOSAL_TASK_DICT, task_proposals)
                    self._interface_connector.update_user_context(UserConversationContext(
                        social_details=user_account.social_details,
                        context=context,
                        version=UserConversationContext.VERSION_V3
                    ))
                    task_creator = service_api.get_user_profile(task.requester_id)
                    if task_creator is None:
                        error_message = "Error: Creator of task [%s] with id [%s] not found by the API" \
                                        % (task.task_id, task.requester_id)
                        logger.error(error_message)
                        creator_name = ""
                    else:
                        creator_name = task_creator.name.first + " " + task_creator.name.last
                    response_message = TextualResponse("There's a task that might interest you:")
                    response = TelegramRapidAnswerResponse(
                        TelegramTextualResponse(emojize(Utils.task_recap_complete(task, creator_name), use_aliases=True)),
                        row_displacement=[1, 2])
                    response.with_textual_option(emojize(":question: More about the task creator", use_aliases=True),
                                                 self.INTENT_CREATOR_INFO.format(proposal_id))
                    response.with_textual_option(emojize(":x: Not interested", use_aliases=True),
                                                 self.INTENT_CANCEL_TASK_PROPOSAL.format(proposal_id))
                    response.with_textual_option(emojize(":white_check_mark: I'm interested", use_aliases=True),
                                                 self.INTENT_CONFIRM_TASK_PROPOSAL.format(proposal_id))
                    logger.info(f"Sent proposal to user [{message.receiver_id}] regarding task [{task.task_id}]")

                    return NotificationEvent(user_account.social_details, [response_message, response], context)
                except KeyError:
                    error_message = "Wrong parsing of the task representation. Not able to find either the location" \
                                    " or the max people that can attend. Got %s" % str(task.to_repr())
                    logger.error(error_message)
            elif isinstance(message, TaskVolunteerNotification):
                # a volunteer has applied to a task, and the task creator is notified
                user_object = service_api.get_user_profile(str(message.volunteer_id))
                if user_object is None:
                    error_message = "Error, userId [%s] does not give any user profile" % str(message.volunteer_id)
                    logger.error(error_message)
                    self._interface_connector.update_user_context(UserConversationContext(
                        social_details=user_account.social_details,
                        context=context,
                        version=UserConversationContext.VERSION_V3
                    ))
                    raise ValueError(error_message)
                candidatures = context.get_static_state(self.CONTEXT_VOLUNTEER_CANDIDATURE_DICT, {})
                candidature_id = str(uuid4()).replace('-', '')[:20]
                candidatures[candidature_id] = {
                    "task": task.task_id,
                    "user": message.volunteer_id
                }
                context.with_static_state(self.CONTEXT_VOLUNTEER_CANDIDATURE_DICT, candidatures)
                user_name = "%s %s" % (user_object.name.first, user_object.name.last)
                message_text = "%s is interested in your event: *%s*! Do you want to accept his application?" \
                               % (user_name, task.goal.name)
                response = TelegramRapidAnswerResponse(TextualResponse(message_text), row_displacement=[1, 2])
                response.with_textual_option(emojize(":question: More about the volunteer", use_aliases=True),
                                             self.INTENT_VOLUNTEER_INFO.format(candidature_id))
                response.with_textual_option(emojize(":x: Not accept", use_aliases=True),
                                             self.INTENT_CANCEL_VOLUNTEER_PROPOSAL.format(candidature_id))
                response.with_textual_option(emojize(":white_check_mark: Yes, why not!?!", use_aliases=True),
                                             self.INTENT_CONFIRM_VOLUNTEER_PROPOSAL.format(candidature_id))
                self._interface_connector.update_user_context(UserConversationContext(
                        social_details=user_account.social_details,
                        context=context,
                        version=UserConversationContext.VERSION_V3
                    ))
                logger.info(f"Sent volunteer [{message.volunteer_id}] candidature to task [{task.task_id}] created by user [{message.receiver_id}]")
                return NotificationEvent(user_account.social_details, [response], context)
            elif isinstance(message, TaskSelectionNotification):
                if message.outcome == TaskSelectionNotification.OUTCOME_ACCEPTED:
                    text = ":tada: I'm happy to announce that the creator accepted you for the event: *%s*" \
                           % task.goal.name
                elif message.outcome == TaskSelectionNotification.OUTCOME_REFUSED:
                    text = "I'm very sorry :pensive:, the creator didn't accept you for the event: *%s*" \
                           % task.goal.name
                else:
                    logger.error("Outcome [%s] unrecognized" % message.outcome)
                    raise Exception("Outcome [%s] unrecognized" % message.outcome)
                logger.info(f"Sent volunteer proposal decision to user [{message.receiver_id}] with outcome {message.outcome}")
                response = TextualResponse(emojize(text, use_aliases=True))
                return NotificationEvent(user_account.social_details, [response])
            elif isinstance(message, TaskConcludedNotification):
                # notify users that a task they were participating is now over
                text = f"The task *{task.goal.name}* that you were participating to is now over. " \
                       f"Its outcome is _{message.outcome}_."
                response = TextualResponse(emojize(text, use_aliases=True))
                return NotificationEvent(user_account.social_details, [response])
            else:
                raise Exception(f"Unrecognized message of type {type(message)}")
        except RefreshTokenExpiredError:
            logger.exception("Refresh token is not longer valid")
            notification_event = NotificationEvent(social_details=user_account.social_details)
            notification_event.with_message(
                TelegramTextualResponse(
                    f"Sorry, the login credential are no longer valid, please login again in order to continue to use the bot:\n "
                    f"{self.wenet_authentication_url}/login?client_id={self.app_id}&external_id={user_account.social_details.get_user_id()}",
                    parse_mode=None)
            )
            return notification_event

    def handle_wenet_authentication_result(self, message: WeNetAuthenticationEvent) -> NotificationEvent:

        if not isinstance(self._connector, TelegramSocialConnector):
            raise Exception("Expected telegram social connector")

        social_details = TelegramDetails(int(message.external_id), int(message.external_id), self._connector.get_telegram_bot_id())
        try:
            self._save_wenet_and_telegram_user_id_to_context(message, social_details)

            text_0 = TextualResponse(emojize("Hello, welcome to the Wenet eat together chatbot :hugging_face:", use_aliases=True))

            text_1 = TextualResponse(("Now you are part of the community! "
                                      "Are you curious to join new experiences and make your social network even more diverse and exciting?\n"
                                      "Well, here is how I can help you!"))
            text_2 = TextualResponse("Type one the following commands to start chatting with me:\n" + self._get_command_list())

            notification = NotificationEvent(
                social_details=social_details,
                messages=[
                    text_0,
                    text_1,
                    text_2
                ]
            )

            return notification

        except Exception as e:
            logger.exception("Unable to complete the wenet login", exc_info=e)
            return NotificationEvent(social_details).with_message(
                TextualResponse("Unable to complete the WeNetAuthentication")
            )

    def action_error(self, incoming_event: IncomingSocialEvent, _: str) -> OutgoingEvent:
        """
        General error handler
        """
        response = OutgoingEvent(social_details=incoming_event.social_details)
        response.with_message(TextualResponse(emojize("I'm very sorry but I didn't understand :pensive:",
                                                      use_aliases=True)))
        return response

    def cancel_action(self, incoming_event: IncomingSocialEvent, _: str) -> OutgoingEvent:
        """
        Cancel the current operation - e.g. the ongoing creation of a task
        """
        to_remove = [self.CONTEXT_CURRENT_STATE, self.CONTEXT_ORGANIZE_TASK_OBJECT, self.CONTEXT_PROPOSAL_TASK_DICT,
                     self.CONTEXT_USER_TASK_LIST, self.CONTEXT_USER_TASK_INDEX, self.CONTEXT_USER_TASK_ACTION]
        context = incoming_event.context
        for context_key in to_remove:
            if context.has_static_state(context_key):
                context.delete_static_state(context_key)
        response = OutgoingEvent(social_details=incoming_event.social_details)
        response.with_context(context)
        response.with_message(TextualResponse("The current operation has been cancelled successfully"))
        return response

    def action_info(self, incoming_event: IncomingSocialEvent, _: str) -> OutgoingEvent:
        """
        Handle the info message, showing the list of available commands
        """
        text_1 = "Type one the following commands to start chatting with me:\n" + self._get_command_list()
        response = OutgoingEvent(social_details=incoming_event.social_details)
        response.with_message(TextualResponse(text_1))
        return response

    def action_start(self, incoming_event: IncomingSocialEvent, intent: str) -> OutgoingEvent:
        return self.action_info(incoming_event, intent)

    def _ask_question(self, incoming_event: IncomingSocialEvent, message: str, state: str) -> OutgoingEvent:
        """
        Internal handler for the various steps of a task creation
        """
        context = incoming_event.context
        context.with_static_state(self.CONTEXT_CURRENT_STATE, state)
        response = OutgoingEvent(social_details=incoming_event.social_details)
        response.with_context(context)
        response.with_message(TextualResponse(emojize(message, use_aliases=True)))
        return response

    def organize_q1(self, incoming_event: IncomingSocialEvent, _: str) -> OutgoingEvent:
        """
        Step 1 of task creation
        """
        logger.debug(f"Organizer q1 for event: {incoming_event}")
        message = ("Q1: :calendar: When do you want to organize the social meal?"
                   "(remember to specify both the date and time, in the following format: "
                   "`<YYYY> <MM> <DD> <HH> <mm>` - e.g. `2020 05 13 13 00`)")
        return self._ask_question(incoming_event, message, self.ORGANIZE_Q1)

    def organize_q2(self, incoming_event: IncomingSocialEvent, _: str) -> OutgoingEvent:
        """
        Step 2 of task creation [timestamp]
        """
        if isinstance(incoming_event.incoming_message, IncomingTextMessage):
            text = incoming_event.incoming_message.text
            timestamp = Utils.parse_datetime(text)
            wenet_id = incoming_event.context.get_static_state(self.CONTEXT_WENET_USER_ID)
            if timestamp is not None:
                end_ts = timestamp + timedelta(hours=1)
                attributes = {
                    "startTs": int(timestamp.timestamp()),
                }
                task = Task(
                    None,
                    int(datetime.now().timestamp()),
                    int(datetime.now().timestamp()),
                    str(self.task_type_id),
                    str(wenet_id),
                    self.app_id,
                    self.community_id,
                    TaskGoal("", ""),
                    [],
                    attributes,
                    int(end_ts.timestamp()),
                    []
                )
                incoming_event.context.with_static_state(self.CONTEXT_ORGANIZE_TASK_OBJECT, task.to_repr())
                message = "Q2: :round_pushpin: Where will it take place?"
                return self._ask_question(incoming_event, message, self.ORGANIZE_Q2)
            else:
                message = ("The format you used for specifying the date and time is not valid. Please stick with: "
                           "`<YYYY> <MM> <DD> <HH> <mm>` (e.g. `2020 05 13 13 00`)")
                return self._ask_question(incoming_event, message, self.ORGANIZE_Q1)
        else:
            message = ("Please write me the date and the time of your event, "
                       "or type /cancel to cancel the current operation")
            return self._ask_question(incoming_event, message, self.ORGANIZE_Q1)

    def organize_q3(self, incoming_event: IncomingSocialEvent, _: str) -> OutgoingEvent:
        """
        Step 3 of task creation [where]
        """
        if isinstance(incoming_event.incoming_message, IncomingTextMessage):
            text = incoming_event.incoming_message.text
            task = Task.from_repr(incoming_event.context.get_static_state(self.CONTEXT_ORGANIZE_TASK_OBJECT))
            task.attributes["where"] = text
            incoming_event.context.with_static_state(self.CONTEXT_ORGANIZE_TASK_OBJECT, task.to_repr())
            message = ("Q3: :alarm_clock: By when do you want to receive applications? "
                       "Please use the following format: "
                       "`<YYYY> <mm> <dd> <HH> <MM>` - e.g. `2020 05 13 13 00`)")
            return self._ask_question(incoming_event, message, self.ORGANIZE_Q3)
        else:
            message = ("Please write me where the event will take place, "
                       "or type /cancel to cancel the current operation")
            return self._ask_question(incoming_event, message, self.ORGANIZE_Q2)

    def organize_q4(self, incoming_event: IncomingSocialEvent, _: str) -> OutgoingEvent:
        """
        Step 4 of task creation [subscription deadline]
        """
        if isinstance(incoming_event.incoming_message, IncomingTextMessage):
            text = incoming_event.incoming_message.text
            timestamp = Utils.parse_datetime(text)
            if timestamp is not None:
                task = Task.from_repr(incoming_event.context.get_static_state(self.CONTEXT_ORGANIZE_TASK_OBJECT))
                task.attributes["deadlineTs"] = int(timestamp.timestamp())
                incoming_event.context.with_static_state(self.CONTEXT_ORGANIZE_TASK_OBJECT, task.to_repr())
                message = "Q4: :couple: How many people can attend?"
                return self._ask_question(incoming_event, message, self.ORGANIZE_Q4)
            else:
                message = ("The format you used for specifying the date and time is not valid. Please stick with: "
                           "`<YYYY> <mm> <dd> <HH> <MM>` (e.g. `2020 05 13 13 00`)")
                return self._ask_question(incoming_event, message, self.ORGANIZE_Q3)
        else:
            message = ("Please write me by when you want to receive applications, "
                       "or type /cancel to cancel the current operation")
            return self._ask_question(incoming_event, message, self.ORGANIZE_Q3)

    def organize_q5(self, incoming_event: IncomingSocialEvent, _: str) -> OutgoingEvent:
        """
        Step 5 of task creation [maxPeople]
        """
        if isinstance(incoming_event.incoming_message, IncomingTextMessage):
            text = incoming_event.incoming_message.text
            task = Task.from_repr(incoming_event.context.get_static_state(self.CONTEXT_ORGANIZE_TASK_OBJECT))
            task.attributes["maxPeople"] = text
            incoming_event.context.with_static_state(self.CONTEXT_ORGANIZE_TASK_OBJECT, task.to_repr())
            message = "Q5: Name of your event:"
            return self._ask_question(incoming_event, message, self.ORGANIZE_Q5)
        else:
            message = ("Please write me how many people can attend to your event, "
                       "or type /cancel to cancel the current operation")
            return self._ask_question(incoming_event, message, self.ORGANIZE_Q4)

    def organize_q6(self, incoming_event: IncomingSocialEvent, _: str) -> OutgoingEvent:
        """
        Step 6 of task creation [task name]
        """
        if isinstance(incoming_event.incoming_message, IncomingTextMessage):
            text = incoming_event.incoming_message.text
            task = Task.from_repr(incoming_event.context.get_static_state(self.CONTEXT_ORGANIZE_TASK_OBJECT))
            task.goal.name = text
            incoming_event.context.with_static_state(self.CONTEXT_ORGANIZE_TASK_OBJECT, task.to_repr())
            message = "Q6: Set a description to share some more details!"
            return self._ask_question(incoming_event, message, self.ORGANIZE_Q6)
        else:
            message = ("Please write me the name of your event, "
                       "or type /cancel to cancel the current operation")
            return self._ask_question(incoming_event, message, self.ORGANIZE_Q5)

    def organize_recap_message(self, incoming_event: IncomingSocialEvent, _: str) -> OutgoingEvent:
        """
        Final recap of the task created [description]
        """
        if isinstance(incoming_event.incoming_message, IncomingTextMessage):
            context = incoming_event.context
            description = incoming_event.incoming_message.text
            task = Task.from_repr(context.get_static_state(self.CONTEXT_ORGANIZE_TASK_OBJECT))
            task.goal.description = description
            context.with_static_state(self.CONTEXT_ORGANIZE_TASK_OBJECT, task.to_repr())
            context.with_static_state(self.CONTEXT_CURRENT_STATE, self.ORGANIZE_RECAP)
            response = OutgoingEvent(social_details=incoming_event.social_details)
            response.with_context(context)
            response.with_message(TextualResponse("Super! Your event is ready, let's have a check:"))
            recap = RapidAnswerResponse(TelegramTextualResponse(emojize(Utils.task_recap_without_creator(task),
                                                                        use_aliases=True)))
            recap.with_textual_option(emojize(":x: Cancel", use_aliases=True), self.INTENT_CANCEL_TASK_CREATION)
            recap.with_textual_option(emojize(":white_check_mark: Confirm", use_aliases=True),
                                      self.INTENT_CONFIRM_TASK_CREATION)
            response.with_message(recap)
            return response
        else:
            message = ("Please write me a description of your event, "
                       "or type /cancel to cancel the current operation")
            return self._ask_question(incoming_event, message, self.ORGANIZE_Q6)

    def action_cancel_task_creation(self, incoming_event: IncomingSocialEvent, _: str) -> OutgoingEvent:
        """
        The task creation is cancelled
        """
        context = incoming_event.context
        context.delete_static_state(self.CONTEXT_ORGANIZE_TASK_OBJECT)
        context.delete_static_state(self.CONTEXT_CURRENT_STATE)
        response = OutgoingEvent(social_details=incoming_event.social_details)
        response.with_message(TextualResponse("All the information have been discarded"))
        response.with_context(context)
        return response

    def action_confirm_task_creation(self, incoming_event: IncomingSocialEvent, _: str) -> OutgoingEvent:
        """
        The task creation is confirmed. The task is created
        """
        if incoming_event.context is not None:
            service_api = self._get_service_api_interface_connector_from_context(incoming_event.context)
        else:
            raise Exception(f"Missing conversation context for event {incoming_event}")
        context = incoming_event.context
        task = Task.from_repr(context.get_static_state(self.CONTEXT_ORGANIZE_TASK_OBJECT))
        context.delete_static_state(self.CONTEXT_ORGANIZE_TASK_OBJECT)
        context.delete_static_state(self.CONTEXT_CURRENT_STATE)
        response = OutgoingEvent(social_details=incoming_event.social_details)
        try:
            service_api.create_task(task)
            logger.info("Task [%s] created successfully by user [%s]" % (task.goal.name, str(task.requester_id)))
            response.with_message(TextualResponse(emojize("Your event has been saved successfully :tada:",
                                                          use_aliases=True)))
        except CreationError as e:
            logger.error(f"The service API responded with code {e.http_status_code} and message {json.dumps(e.server_response)}")
            response.with_message(TextualResponse("I'm sorry, but something went wrong with the creation of your task."
                                                  " Try again later"))
        finally:
            response.with_context(context)
            return response

    def action_confirm_task_proposal(self, incoming_event: IncomingSocialEvent, _: str) -> OutgoingEvent:
        """
        A volunteer confirms its application to a task. Transaction sent
        """
        if incoming_event.context is not None:
            service_api = self._get_service_api_interface_connector_from_context(incoming_event.context)
        else:
            raise Exception(f"Missing conversation context for event {incoming_event}")

        context = incoming_event.context
        task_dict = context.get_static_state(self.CONTEXT_PROPOSAL_TASK_DICT, {})
        intent = incoming_event.incoming_message.intent.value
        proposal_id = intent.split('_')[1]
        if proposal_id not in task_dict:
            return self.handle_expired_click(incoming_event, "")
        task = Task.from_repr(task_dict[proposal_id]["task"])
        volunteer_id = task_dict[proposal_id]["user"]
        task_dict.pop(proposal_id, None)
        response = OutgoingEvent(social_details=incoming_event.social_details)
        response.with_context(context)
        try:
            transaction = TaskTransaction(None, task.task_id, self.LABEL_VOLUNTEER_FOR_TASK,
                                          int(datetime.now().timestamp()), int(datetime.now().timestamp()),
                                          volunteer_id, {}, [])
            service_api.create_task_transaction(transaction)

            logger.info("Sent task transaction: %s" % str(transaction.to_repr()))
            response.with_message(TextualResponse(emojize("Great! I immediately send a notification to the task creator! "
                                                          "I'll let you know if you are selected to participate :wink:",
                                                          use_aliases=True)))
        except CreationError as e:
            response.with_message(TextualResponse("I'm sorry, something went wrong, try again later"))
            error_message = "Error in the creation of the transaction for confirming the partecipation of user" \
                            " [%s] to task [%s]. The service API resonded with code %d and message %s" \
                            % (volunteer_id, task.task_id, e.http_status_code, json.dumps(e.server_response))
            logger.error(error_message)
        return response

    def action_delete_task_proposal(self, incoming_event: IncomingSocialEvent, _: str) -> OutgoingEvent:
        """
        A volunteer does not apply to a task. A transaction is sent
        """
        if incoming_event.context is not None:
            service_api = self._get_service_api_interface_connector_from_context(incoming_event.context)
        else:
            raise Exception(f"Missing conversation context for event {incoming_event}")

        context = incoming_event.context
        task_dict = context.get_static_state(self.CONTEXT_PROPOSAL_TASK_DICT, {})
        intent = incoming_event.incoming_message.intent.value
        proposal_id = intent.split('_')[1]
        task = Task.from_repr(task_dict[proposal_id]["task"])
        volunteer_id = task_dict[proposal_id]["user"]
        if proposal_id not in task_dict:
            return self.handle_expired_click(incoming_event, "")
        task_dict.pop(proposal_id, None)
        try:
            transaction = TaskTransaction(None, task.task_id, self.LABEL_REFUSE_TASK, int(datetime.now().timestamp()),
                                          int(datetime.now().timestamp()), volunteer_id, {}, [])
            service_api.create_task_transaction(transaction)
            logger.info("Sent task transaction: %s" % str(transaction.to_repr()))
        except CreationError as e:
            error_message = "Error in the creation of the transaction for communicating that the user" \
                            " [%s] refused to participate to task [%s]. " \
                            "The service API resonded with code %d and message %s" \
                            % (volunteer_id, task.task_id, e.http_status_code, json.dumps(e.server_response))
            logger.error(error_message)
        response = OutgoingEvent(social_details=incoming_event.social_details)
        response.with_message(TextualResponse(emojize("All right :+1:", use_aliases=True)))
        response.with_context(context)
        return response

    def handle_help(self, message: IncomingSocialEvent, _: str) -> OutgoingEvent:
        """
        General help message
        """
        response = OutgoingEvent(social_details=message.social_details)
        help_text = "These are the commands you can use with this chatbot:\n" + self._get_command_list()
        response.with_message(TextualResponse(help_text))
        return response

    def handle_oauth_login(self, message: IncomingSocialEvent, _: str) -> OutgoingEvent:
        response = OutgoingEvent(social_details=message.social_details)
        response.with_message(
            TelegramTextualResponse(f"To use the bot you must first authorize access on the WeNet platform: "
                                    f"{self.wenet_authentication_url}/login?client_id={self.app_id}&external_id={message.social_details.get_user_id()}",
                                    parse_mode=None)
        )
        return response

    def handle_volunteer_info(self, message: IncomingSocialEvent, _: str) -> OutgoingEvent:
        """
        Display information about a volunteer that is applying for a task
        """
        if message.context is not None:
            service_api = self._get_service_api_interface_connector_from_context(message.context)
        else:
            raise Exception(f"Missing conversation context for event {message}")

        intent = message.incoming_message.intent.value
        candidatures = message.context.get_static_state(self.CONTEXT_VOLUNTEER_CANDIDATURE_DICT, {})
        candidature_id = intent.split('_')[1]
        if candidature_id not in candidatures:
            return self.handle_expired_click(message, "")
        user_id = candidatures[candidature_id]["user"]
        response = OutgoingEvent(social_details=message.social_details)
        user_object = service_api.get_user_profile(str(user_id))
        if user_object is None:
            error_message = "Error, userId [%s] does not give any user profile" % str(user_id)
            logger.error(error_message)
            raise ValueError(error_message)
        response.with_message(TextualResponse("The volunteer is *%s %s*" % (user_object.name.first, user_object.name.last)))
        menu = RapidAnswerResponse(TextualResponse("So, what do you want to do?"))
        menu.with_textual_option(emojize(":x: Not accept", use_aliases=True),
                                 self.INTENT_CANCEL_VOLUNTEER_PROPOSAL.format(candidature_id))
        menu.with_textual_option(emojize(":white_check_mark: Yes, of course!", use_aliases=True),
                                 self.INTENT_CONFIRM_VOLUNTEER_PROPOSAL.format(candidature_id))
        response.with_message(menu)
        response.with_context(message.context)
        return response

    def _handle_volunteer_proposal(self, message: IncomingSocialEvent, decision: bool) -> (bool, ConversationContext):
        """
        Internal function used to handle the creator's decision of either accept or refuse a volunteer.
        In any case, a transaction is sent
        """
        if message.context is not None:
            service_api = self._get_service_api_interface_connector_from_context(message.context)
        else:
            raise Exception(f"Missing conversation context for event {message}")

        candidatures = message.context.get_static_state(self.CONTEXT_VOLUNTEER_CANDIDATURE_DICT, {})
        intent = message.incoming_message.intent.value
        candidature_id = intent.split('_')[1]
        if candidature_id not in candidatures:
            raise ValueError("No candidature found")
        volunteer_id = candidatures[candidature_id]["user"]
        task_id = candidatures[candidature_id]["task"]
        creator_id = message.context.get_static_state(self.CONTEXT_WENET_USER_ID)
        task_label = self.LABEL_ACCEPT_VOLUNTEER if decision else self.LABEL_REFUSE_VOLUNTEER
        transaction = TaskTransaction(None, task_id, task_label, int(datetime.now().timestamp()),
                                      int(datetime.now().timestamp()), creator_id, {"volunteerId": volunteer_id}, [])
        try:
            service_api.create_task_transaction(transaction)
            logger.info("Sent task transaction: %s" % str(transaction.to_repr()))
            outcome = True
        except CreationError as e:
            logger.error("Error in the creation of the transaction with creator decision about the partecipation of user"
                         " [%s] to task [%s]. The service API resonded with code %d and message %s"
                         % (volunteer_id, task_id, e.http_status_code, json.dumps(e.server_response)))
            outcome = False
        finally:
            candidatures.pop(candidature_id, None)
            message.context.with_static_state(self.CONTEXT_VOLUNTEER_CANDIDATURE_DICT, candidatures)
        return outcome, message.context

    def handle_confirm_candidature(self, incoming_event: IncomingSocialEvent, _: str) -> OutgoingEvent:
        """
        The creator confirms a volunteer's candidature
        """
        response = OutgoingEvent(social_details=incoming_event.social_details)
        try:
            result, context = self._handle_volunteer_proposal(incoming_event, True)
            if result:
                response.with_message(TextualResponse("Great, you have accepted the volunteer!"))
            else:
                response.with_message(TextualResponse("I'm sorry, but something went wrong"))
            response.with_context(context)
            return response
        except ValueError:
            return self.handle_expired_click(incoming_event, "")

    def handle_reject_candidature(self, incoming_event: IncomingSocialEvent, _: str) -> OutgoingEvent:
        """
        The creator refuses a volunteer's candidature
        """
        response = OutgoingEvent(social_details=incoming_event.social_details)
        try:
            result, context = self._handle_volunteer_proposal(incoming_event, False)
            if result:
                response.with_message(TextualResponse("Ok, you have rejected the volunteer!"))
            else:
                response.with_message(TextualResponse("I'm sorry, but something went wrong"))
            response.with_context(context)
            return response
        except ValueError:
            return self.handle_expired_click(incoming_event, "")

    def get_creator_info(self, incoming_event: IncomingSocialEvent, _: str) -> OutgoingEvent:
        """
        Display information about a creator, when a volunteer is applying to a task
        """
        if incoming_event.context is not None:
            service_api = self._get_service_api_interface_connector_from_context(incoming_event.context)
        else:
            raise Exception(f"Missing conversation context for event {incoming_event}")

        context = incoming_event.context
        task_dict = context.get_static_state(self.CONTEXT_PROPOSAL_TASK_DICT, {})
        intent = incoming_event.incoming_message.intent.value
        proposal_id = intent.split('_')[1]
        if proposal_id not in task_dict:
            return self.handle_expired_click(incoming_event, "")
        task = Task.from_repr(task_dict[proposal_id]["task"])
        # getting user information
        creator = service_api.get_user_profile(task.requester_id)
        if creator is None:
            error_message = "Illegal state: task [%s] creator is None" % task.task_id
            logger.error(error_message)
            self._alert_module.alert(error_message)
            raise ValueError(error_message)
        response = OutgoingEvent(social_details=incoming_event.social_details, context=incoming_event.context)
        response.with_message(TextualResponse("The task is created by *%s %s*" % (creator.name.first, creator.name.last)))
        creator_info_message = RapidAnswerResponse(TextualResponse("What do you want to do?"))
        creator_info_message.with_textual_option(emojize(":x: Not interested", use_aliases=True),
                                                 self.INTENT_CANCEL_TASK_PROPOSAL.format(proposal_id))
        creator_info_message.with_textual_option(emojize(":white_check_mark: I'm interested", use_aliases=True),
                                                 self.INTENT_CONFIRM_TASK_PROPOSAL.format(proposal_id))
        response.with_message(creator_info_message)
        return response

    def _select_task(self, incoming_event: IncomingSocialEvent, initial_message: str, action: str) -> OutgoingEvent:
        """
        Create a carousel that allows a user to select one task among those created by herself
        :param incoming_event: original message
        :param initial_message: starting message to be displayed
        :param action: action performed by the user (e.g. concluding a task)
        """
        if incoming_event.context is not None:
            service_api = self._get_service_api_interface_connector_from_context(incoming_event.context)
        else:
            raise Exception(f"Missing conversation context for event {incoming_event}")

        context = incoming_event.context
        response = OutgoingEvent(social_details=incoming_event.social_details, context=context)

        if not context.has_static_state(self.CONTEXT_WENET_USER_ID):
            error_message = "WeNet User ID not saved in the context for user [%d]" % incoming_event.social_details.get_user_id()
            logger.error(error_message)
            self._alert_module.alert(error_message)
            raise ValueError(error_message)
        wenet_id = context.get_static_state(self.CONTEXT_WENET_USER_ID)
        task_list = service_api.get_opened_tasks_of_user(str(wenet_id), self.app_id)
        # filter on the malformed tasks (those without "where" and "maxPeople" attributes)
        task_list = [x for x in task_list if "where" in x.attributes and "maxPeople" in x.attributes]
        if len(task_list) > 0:
            context.with_static_state(self.CONTEXT_USER_TASK_LIST, [t.to_repr() for t in task_list])
            context.with_static_state(self.CONTEXT_USER_TASK_INDEX, 0)
            context.with_static_state(self.CONTEXT_USER_TASK_ACTION, action)
            response.with_message(TelegramTextualResponse(emojize(initial_message, use_aliases=True)))
            carousel = TelegramCarouselResponse(TelegramTextualResponse(emojize(Utils.task_recap_without_creator(task_list[0]), use_aliases=True)),
                                                None,
                                                TelegramCallbackButton.build_for_carousel("Next", self.INTENT_TASK_LIST_NEXT) if len(task_list) > 1 else None,
                                                [TelegramCallbackButton.build_for_carousel(emojize(":x: Cancel", use_aliases=True), self.INTENT_TASK_LIST_CANCEL),
                                                 TelegramCallbackButton.build_for_carousel(emojize(":white_check_mark: Select", use_aliases=True), self.INTENT_TASK_LIST_CONFIRM)],
                                                [2])
            response.with_message(carousel)
        else:
            response.with_message(TextualResponse("There are no tasks created by you"))

        return response

    def action_conclude_select_task(self, incoming_event: IncomingSocialEvent, _: str) -> OutgoingEvent:
        """
        Give the user the list of the tasks she opened, using a carousel
        """
        inital_message = "Select the task you want to conclude :point_down:. Use the buttons _Previous_ and _Next_ to navigate through your open tasks"
        incoming_event.context.with_static_state(self.CONTEXT_CURRENT_STATE, self.TASK_ACTION_CONCLUDE)
        return self._select_task(incoming_event, inital_message, self.TASK_ACTION_CONCLUDE)

    def _handle_telegram_carousel_response(self, message: IncomingTelegramCarouselCommand) -> Optional[TelegramCarouselResponse]:
        """
        Handle the carousel usage, in this case used to navigate through the tasks created by a user and to select one
        """
        if not isinstance(self._connector, TelegramSocialConnector):
            raise Exception("Expected telegram social connector")

        recipient_details = TelegramDetails(message.user_id, message.chat_id, self._connector.get_telegram_bot_id())
        context = self._interface_connector.get_user_context(recipient_details)
        if not context.context.has_static_state(self.CONTEXT_USER_TASK_LIST):
            error_message = "Illegal state: no list of tasks of a user when trying to select one"
            logger.error(error_message)
            self._alert_module.alert(error_message)
            raise ValueError(error_message)
        if not context.context.has_static_state(self.CONTEXT_USER_TASK_INDEX):
            error_message = "Illegal state: no index of the list of tasks of a user when trying to select one"
            logger.error(error_message)
            self._alert_module.alert(error_message)
            raise ValueError(error_message)
        if not context.context.has_static_state(self.CONTEXT_USER_TASK_ACTION):
            error_message = "Illegal state: no user action when the user is trying to select a task"
            logger.error(error_message)
            self._alert_module.alert(error_message)
            raise ValueError(error_message)
        task_list = [Task.from_repr(task) for task in context.context.get_static_state(self.CONTEXT_USER_TASK_LIST, [])]
        current_index = context.context.get_static_state(self.CONTEXT_USER_TASK_INDEX)
        user_action = context.context.get_static_state(self.CONTEXT_USER_TASK_ACTION)
        if user_action == self.TASK_ACTION_CONCLUDE:
            # the user is concluding a task
            if message.command == self.INTENT_TASK_LIST_NEXT:
                # the user clicked on the next button to navigate the list of its tasks
                current_index += 1
                carousel_update = TelegramCarouselResponse(
                    TelegramTextualResponse(emojize(Utils.task_recap_without_creator(task_list[current_index]), use_aliases=True)),
                    TelegramCallbackButton.build_for_carousel("Previous", self.INTENT_TASK_LIST_PREVIOUS),
                    TelegramCallbackButton.build_for_carousel("Next", self.INTENT_TASK_LIST_NEXT) if current_index + 1 < len(task_list) else None,
                    [TelegramCallbackButton.build_for_carousel(emojize(":x: Cancel", use_aliases=True),
                                                               self.INTENT_TASK_LIST_CANCEL),
                     TelegramCallbackButton.build_for_carousel(emojize(":white_check_mark: Select", use_aliases=True),
                                                               self.INTENT_TASK_LIST_CONFIRM)],
                    [2]
                )
                context.context.with_static_state(self.CONTEXT_USER_TASK_INDEX, current_index)
            elif message.command == self.INTENT_TASK_LIST_PREVIOUS:
                # the user clicked on the previous button to navigate the list of its tasks
                current_index -= 1
                carousel_update = TelegramCarouselResponse(
                    TelegramTextualResponse(
                        emojize(Utils.task_recap_without_creator(task_list[current_index]), use_aliases=True)),
                    TelegramCallbackButton.build_for_carousel("Previous", self.INTENT_TASK_LIST_PREVIOUS) if current_index > 0 else None,
                    TelegramCallbackButton.build_for_carousel("Next", self.INTENT_TASK_LIST_NEXT),
                    [TelegramCallbackButton.build_for_carousel(emojize(":x: Cancel", use_aliases=True),
                                                               self.INTENT_TASK_LIST_CANCEL),
                     TelegramCallbackButton.build_for_carousel(emojize(":white_check_mark: Select", use_aliases=True),
                                                               self.INTENT_TASK_LIST_CONFIRM)],
                    [2]
                )
                context.context.with_static_state(self.CONTEXT_USER_TASK_INDEX, current_index)
            elif message.command == self.INTENT_TASK_LIST_CANCEL:
                # the user wants to cancel the current operation. This intent will be handled also externally by a custom function
                carousel_update = None
                context.context.delete_static_state(self.CONTEXT_USER_TASK_LIST)
                context.context.delete_static_state(self.CONTEXT_USER_TASK_INDEX)
                context.context.delete_static_state(self.CONTEXT_USER_TASK_ACTION)
            elif message.command == self.INTENT_TASK_LIST_CONFIRM:
                # the user has selected a task. This intent will be handled also externally by a custom function
                carousel_update = None
                context.context.delete_static_state(self.CONTEXT_USER_TASK_ACTION)
            else:
                error_message = "Error, unrecognize command [%s] of the task selection carousel" % message.command
                logger.error(error_message)
                self._alert_module.alert(error_message)
                raise ValueError(error_message)
        else:
            error_message = "Error, user action [%s] unrecognized" % user_action
            logger.error(error_message)
            self._alert_module.alert(error_message)
            raise ValueError(error_message)
        self._interface_connector.update_user_context(context)
        return carousel_update

    def action_task_conclusion_cancel(self, incoming_event: IncomingSocialEvent, _: str) -> OutgoingEvent:
        """
        The user deleted the operation of closing a task
        """
        response = OutgoingEvent(social_details=incoming_event.social_details)
        response.with_message(TextualResponse(emojize("The operation has been cancelled :+1:", use_aliases=True)))
        incoming_event.context.delete_static_state(self.CONTEXT_CURRENT_STATE)
        incoming_event.context.delete_static_state(self.CONTEXT_USER_TASK_LIST)
        incoming_event.context.delete_static_state(self.CONTEXT_USER_TASK_INDEX)
        response.with_context(incoming_event.context)
        return response

    def action_conclude_task(self, incoming_event: IncomingSocialEvent, _: str) -> OutgoingEvent:
        """
        The user has selected a task to be concluded, and she is asked how to close it
        """
        response = OutgoingEvent(social_details=incoming_event.social_details)
        question = TelegramRapidAnswerResponse(TextualResponse("What is the outcome of the task?"), row_displacement=[1, 1, 1])
        question.with_textual_option("Completed", self.INTENT_OUTCOME_COMPLETED)
        question.with_textual_option("Cancelled", self.INTENT_OUTCOME_CANCELLED)
        question.with_textual_option("Failed", self.INTENT_OUTCOME_FAILED)
        response.with_message(question)
        return response

    def action_conclude_task_send_transaction(self, incoming_event: IncomingSocialEvent, intent: str) -> OutgoingEvent:
        """
        Create a transaction with the outcome of the task
        """
        if incoming_event.context is not None:
            service_api = self._get_service_api_interface_connector_from_context(incoming_event.context)
        else:
            raise Exception(f"Missing conversation context for event {incoming_event}")

        context = incoming_event.context
        actioneer_id = incoming_event.context.get_static_state(self.CONTEXT_WENET_USER_ID)
        if not context.has_static_state(self.CONTEXT_USER_TASK_LIST):
            error_message = "Illegal state: no list of tasks of a user when trying to close one"
            logger.error(error_message)
            self._alert_module.alert(error_message)
            raise ValueError(error_message)
        if not context.has_static_state(self.CONTEXT_USER_TASK_INDEX):
            error_message = "Illegal state: no index of the list of tasks of a user when trying to close one"
            logger.error(error_message)
            self._alert_module.alert(error_message)
            raise ValueError(error_message)
        task_list = [Task.from_repr(task) for task in context.get_static_state(self.CONTEXT_USER_TASK_LIST, [])]
        current_index = context.get_static_state(self.CONTEXT_USER_TASK_INDEX)
        if intent == self.INTENT_OUTCOME_FAILED:
            outcome = "failed"
        elif intent == self.INTENT_OUTCOME_CANCELLED:
            outcome = "cancelled"
        elif intent == self.INTENT_OUTCOME_COMPLETED:
            outcome = "completed"
        else:
            error_message = f"Unrecognize outcome [{intent}] of a task"
            logger.error(error_message)
            raise ValueError(error_message)
        response = OutgoingEvent(social_details=incoming_event.social_details)
        try:
            transaction = TaskTransaction(None, task_list[current_index].task_id, self.LABEL_TASK_COMPLETED,
                                          int(datetime.now().timestamp()), int(datetime.now().timestamp()),
                                          actioneer_id, {"outcome": outcome}, [])
            service_api.create_task_transaction(transaction)
            logger.info("Sent task transaction: %s" % str(transaction.to_repr()))
            response.with_message(TextualResponse("Your task has been closed successfully"))
            context.delete_static_state(self.CONTEXT_USER_TASK_LIST)
            context.delete_static_state(self.CONTEXT_USER_TASK_INDEX)
            context.delete_static_state(self.CONTEXT_CURRENT_STATE)
        except CreationError as e:
            response.with_message(TextualResponse("I'm sorry, something went wrong, try again later"))
            logger.error("Error in the creation of the transaction for concluding the task [%s]. The service API resonded with code %d and message %s"
                         % (task_list[current_index].task_id, e.http_status_code, json.dumps(e.server_response)))

        response.with_context(context)
        return response

    @staticmethod
    def _get_command_list() -> str:
        """
        :return: a markdown string with all the commands available in the chatbot
        """
        return "*/info* for receiving information on this bot\n" \
               "*/organize* to organize a social meal\n" \
               "*/conclude* to close an existing social meal\n" \
               "To interrupt an ongoing procedure at any time, type */cancel*"

    @staticmethod
    def handle_expired_click(incoming_event: IncomingSocialEvent, _: str) -> OutgoingEvent:
        response = OutgoingEvent(social_details=incoming_event.social_details)
        if isinstance(incoming_event.incoming_message, IncomingCommand):
            logger.info("The user clicked on an expired button: %s" % incoming_event.incoming_message.command)
            response.with_message(TextualResponse("Operation not allowed anymore, you clicked on an expired button"))
        return response
