from __future__ import absolute_import, annotations

import uuid
from typing import Union

from chatbot_core.model.message import IncomingMessage, IncomingImage, IncomingLocation, IncomingCommand, \
    IncomingTextMessage
from chatbot_core.v3.model.actions import PostBackButton
from chatbot_core.v3.model.messages import ResponseMessage as ChatbotResponseMessage, TextualResponse, TelegramTextualResponse, \
    RapidAnswerResponse, TelegramRapidAnswerResponse, UrlImageResponse, TelegramCarouselResponse
from wenet.model.logging_message.message import ResponseMessage, RequestMessage, NotificationMessage
from wenet.model.logging_message.content import TextualContent, AttachmentContent, CarouselContent, Card, \
    LocationContent, ActionRequest
from wenet.model.callback_message.event import WeNetAuthenticationEvent
from wenet.model.callback_message.message import TextualMessage, Message


class LogMessageHandler:
    """
    This class converts chatbot messages or messages from Wenet into logging messages.
    Attributes:
        - project: the name of the project in which messages are exchanged
        - channel: the communication channel (FB, Telegram)
    """

    def __init__(self, project: str, channel: str) -> None:
        self.project = project
        self.channel = channel

    def handle_textual_response(self, message: TextualResponse, user_id: str, response_to: str) -> ResponseMessage:
        content = TextualContent(message.text)
        return ResponseMessage(str(uuid.uuid4()), self.channel, user_id, self.project, content, response_to)

    def handle_rapid_answer_response(self, message: RapidAnswerResponse, user_id: str, response_to: str) -> ResponseMessage:
        content = TextualContent(message.text)
        for button in message.options:
            if isinstance(button, PostBackButton):
                content.with_button(button.text, button.payload)
            else:
                content.with_button(button.fallback_text, "")
        return ResponseMessage(str(uuid.uuid4()), self.channel, user_id, self.project, content, response_to)

    def handle_image_url_response(self, message: UrlImageResponse, user_id: str, response_to: str) -> ResponseMessage:
        content = AttachmentContent(message.url)
        return ResponseMessage(str(uuid.uuid4()), self.channel, user_id, self.project, content, response_to)

    def handle_telegram_carousel(self, message: TelegramCarouselResponse, user_id: str, response_to: str) -> ResponseMessage:
        content = CarouselContent([])
        content.with_card(Card(message.message.text)
                          .with_button(message.previous_button.text, message.previous_button.intent)
                          .with_button(message.next_button.text, message.next_button.intent))
        return ResponseMessage(str(uuid.uuid4()), self.channel, user_id, self.project, content, response_to)

    def handle_incoming_image(self, message: IncomingImage, user_id: str) -> RequestMessage:
        content = AttachmentContent(message.image_url)
        return RequestMessage(str(uuid.uuid4()), self.channel, user_id, self.project, content)

    def handle_incoming_location(self, message: IncomingLocation, user_id: str) -> RequestMessage:
        content = LocationContent(message.latitude, message.longitude)
        return RequestMessage(str(uuid.uuid4()), self.channel, user_id, self.project, content)

    def handle_incoming_command(self, message: IncomingCommand, user_id: str) -> RequestMessage:
        content = ActionRequest(message.command)
        return RequestMessage(str(uuid.uuid4()), self.channel, user_id, self.project, content)

    def handle_incoming_text_message(self, message: IncomingTextMessage, user_id: str) -> RequestMessage:
        content = TextualContent(message.text)
        return RequestMessage(str(uuid.uuid4()), self.channel, user_id, self.project, content)

    def handle_wenet_textual_message(self, message: TextualMessage, user_id: str) -> NotificationMessage:
        content = TextualContent(f"{message.title} - {message.text}")
        return NotificationMessage(str(uuid.uuid4()), self.channel, user_id, self.project, content)

    def handle_wenet_message(self, message: Message, user_id: str) -> NotificationMessage:
        content = TextualContent(message.label)
        return NotificationMessage(str(uuid.uuid4()), self.channel, user_id, self.project, content, metadata=message.attributes)

    def handle_authentication_event(self, message: WeNetAuthenticationEvent, user_id: str) -> NotificationMessage:
        content = TextualContent(message.TYPE)
        metadata = {
            "externalId": message.external_id,
            "code": message.code,
        }
        return NotificationMessage(str(uuid.uuid4()), self.channel, user_id, self.project, content, metadata=metadata)

    def create_response(self, message: ChatbotResponseMessage, user_id: str, response_to: str) -> ResponseMessage:
        """
        Given a ResponseMessage of the chatbot core, create a ResponseMessage for the Wenet logging
        """
        if isinstance(message, TelegramRapidAnswerResponse) or isinstance(message, RapidAnswerResponse):
            return self.handle_rapid_answer_response(message, user_id, response_to)
        elif isinstance(message, UrlImageResponse):
            return self.handle_image_url_response(message, user_id, response_to)
        elif isinstance(message, TelegramCarouselResponse):
            return self.handle_telegram_carousel(message, user_id, response_to)
        elif isinstance(message, TextualResponse) or isinstance(message, TelegramTextualResponse):
            return self.handle_textual_response(message, user_id, response_to)
        else:
            raise TypeError(f"Message of type {type(message)} not supported")

    def create_request(self, message: IncomingMessage, user_id: str) -> RequestMessage:
        """
        Given an IncomingMessage of the chatbot core, create a RequestMessage for the Wenet logging
        """
        if isinstance(message, IncomingImage):
            return self.handle_incoming_image(message, user_id)
        elif isinstance(message, IncomingLocation):
            return self.handle_incoming_location(message, user_id)
        elif isinstance(message, IncomingCommand):
            return self.handle_incoming_command(message, user_id)
        elif isinstance(message, IncomingTextMessage):
            return self.handle_incoming_text_message(message, user_id)
        else:
            raise TypeError(f"Message of type {type(message)} not supported")

    def create_notification(self, message: Union[Message, WeNetAuthenticationEvent], user_id: str) -> NotificationMessage:
        """
        Given a message from Wenet, create a NotificationMessage for the Wenet logging
        """
        if isinstance(message, TextualMessage):
            return self.handle_wenet_textual_message(message, user_id)
        elif isinstance(message, Message):
            return self.handle_wenet_message(message, user_id)
        elif isinstance(message, WeNetAuthenticationEvent):
            return self.handle_authentication_event(message, user_id)
        else:
            raise TypeError(f"Message of type {type(message)} not supported")
