import json
import logging

from flask import request, redirect
from flask_restful import Resource, abort

from chatbot_core.model.event import IncomingCustomEvent
from uhopper.utils.mqtt.handler import MqttPublishHandler
from common.authentication_event import WeNetAuthenticationEvent
from common.callback_messages import MessageBuilder

logger = logging.getLogger("uhopper.chatbot.wenet.messages")


class WeNetMessageInterface(Resource):

    def __init__(self, mqtt_publisher: MqttPublishHandler, mqtt_topic: str, instance_namespace: str,
                 bot_id: str) -> None:

        self.mqtt_publisher = mqtt_publisher
        self.instance_namespace = instance_namespace
        self.bot_id = bot_id
        self.mqtt_topic = mqtt_topic

    def post(self):
        data = request.get_json()
        try:
            message = MessageBuilder.build(data)
            logger.info("Message received: [%s] %s" % (type(message), str(message.to_repr())))
            event = IncomingCustomEvent(self.instance_namespace, message.to_repr(), self.bot_id)
            self.mqtt_publisher.publish_data(self.mqtt_topic, event.to_repr())
            return {}, 200
        except KeyError as e:
            logger.exception("Bad payload: parsing error. Received %s" % json.dumps(data), exc_info=e)
            return {"Error": "One or more required keys are missing"}, 400
        except ValueError:
            logger.error("Error, enum values not respected. Received %s" % json.dumps(data))
            return {"Error": "One or more values of the enum fields are not respected. Please check the documentation "
                             "and try again"}, 400


class WeNetLoginCallbackInterface(Resource):

    def __init__(self, mqtt_publisher: MqttPublishHandler, mqtt_topic: str, instance_namespace: str,
                 bot_id: str, wenet_app_id: str, oauth_successful_redirect_url: str) -> None:
        self.mqtt_publisher = mqtt_publisher
        self.instance_namespace = instance_namespace
        self.bot_id = bot_id
        self.mqtt_topic = mqtt_topic
        self._app_id = wenet_app_id
        self.oauth_successful_redirect_url = oauth_successful_redirect_url

    def get(self):

        code: str = request.args.get("code")
        external_id: str = request.args.get("external_id")

        if code is None or code == "" or external_id is None or external_id == "":
            error = request.args.get("error")
            logger.warning(f"Missing authorization code or external id, error {error}")
            abort(400, message="Missing authorization code or external id")
            return

        logger.info(f"Authentication credentials received: code [{code}] and external id [{external_id}]")
        message = WeNetAuthenticationEvent(external_id, code)
        event = IncomingCustomEvent(self.instance_namespace, message.to_repr(), self.bot_id)
        self.mqtt_publisher.publish_data(self.mqtt_topic, event.to_repr())

        logger.debug("event sent")
        return redirect(f"{self.oauth_successful_redirect_url}?app_id={self._app_id}")


class InstanceResourcesBuilder:

    @staticmethod
    def routes(mqtt_publisher: MqttPublishHandler, mqtt_topic: str, instance_namespace: str, bot_id: str, wenet_app_id: str, oauth_successful_redirect_url: str):
        return [
            (WeNetMessageInterface, '/message', (mqtt_publisher, mqtt_topic, instance_namespace, bot_id)),
            (WeNetLoginCallbackInterface, '/auth', (mqtt_publisher, mqtt_topic, instance_namespace, bot_id, wenet_app_id, oauth_successful_redirect_url))
        ]
