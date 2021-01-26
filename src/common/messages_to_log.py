from __future__ import absolute_import, annotations

import uuid

from chatbot_core.v3.model.actions import PostBackButton
from chatbot_core.v3.model.messages import ResponseMessage, TextualResponse, TelegramTextualResponse, \
    RapidAnswerResponse, TelegramRapidAnswerResponse, UrlImageResponse, TelegramCarouselResponse
from wenet.common.model.logging_messages import messages
from wenet.common.model.logging_messages.contents import TextualContent, AttachmentContent, CarouselContent, Card


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

    def handle_textual_response(self, message: TextualResponse, user_id: str) -> messages.ResponseMessage:
        content = TextualContent(message.text)
        return messages.ResponseMessage(str(uuid.uuid4()), self.channel, user_id, self.project, content)

    def handle_rapid_answer_response(self, message: RapidAnswerResponse, user_id: str) -> messages.ResponseMessage:
        content = TextualContent(message.text)
        for button in message.options:
            if isinstance(button, PostBackButton):
                content.with_button(button.text, button.payload)
            else:
                content.with_button(button.fallback_text, "")
        return messages.ResponseMessage(str(uuid.uuid4()), self.channel, user_id, self.project, content)

    def handle_image_url_response(self, message: UrlImageResponse, user_id: str) -> messages.ResponseMessage:
        content = AttachmentContent(message.url)
        return messages.ResponseMessage(str(uuid.uuid4()), self.channel, user_id, self.project, content)

    def handle_telegram_carousel(self, message: TelegramCarouselResponse, user_id: str) -> messages.ResponseMessage:
        content = CarouselContent([])
        content.with_card(Card(message.message.text)
                          .with_button(message.previous_button.text, message.previous_button.intent)
                          .with_button(message.next_button.text, message.next_button.intent))
        return messages.ResponseMessage(str(uuid.uuid4()), self.channel, user_id, self.project, content)

    def create_response(self, message: ResponseMessage, user_id: str) -> messages.ResponseMessage:
        if isinstance(message, TelegramRapidAnswerResponse) or isinstance(message, RapidAnswerResponse):
            return self.handle_rapid_answer_response(message, user_id)
        elif isinstance(message, UrlImageResponse):
            return self.handle_image_url_response(message, user_id)
        elif isinstance(message, TelegramCarouselResponse):
            return self.handle_telegram_carousel(message, user_id)
        elif isinstance(message, TextualResponse) or isinstance(message, TelegramTextualResponse):
            return self.handle_textual_response(message, user_id)
        else:
            raise TypeError(f"Message of type {type(message)} not supported")
