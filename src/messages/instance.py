import json
import logging

from flask import request
from flask_restful import Resource, abort

from chatbot_core.model.event import IncomingCustomEvent
from uhopper.utils.mqtt import MqttPublishHandler
from wenet.common.model.message.builder import MessageBuilder
from wenet.common.model.message.exception import MessageTypeError, NotificationTypeError
from wenet.common.model.message.message import WeNetAuthentication

logger = logging.getLogger("uhopper.chatbot.wenet.eattogether.messages")


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
        except MessageTypeError as e:
            logger.error(e.message)
            return {"Error": e.message}, 400
        except NotificationTypeError as e:
            logger.error(e.message)
            return {"Error": e.message}, 400
        except KeyError:
            logger.error("Bad payload: parsing error. Received %s" % json.dumps(data))
            return {"Error": "One or more required keys are missing"}, 400
        except ValueError:
            logger.error("Error, enum values not respected. Received %s" % json.dumps(data))
            return {"Error": "One or more values of the enum fields are not respected. Please check the documentation "
                             "and try again"}, 400


class WeNetLoginCallbackInterface(Resource):

    def __init__(self, mqtt_publisher: MqttPublishHandler, mqtt_topic: str, instance_namespace: str,
                 bot_id: str) -> None:
        self.mqtt_publisher = mqtt_publisher
        self.instance_namespace = instance_namespace
        self.bot_id = bot_id
        self.mqtt_topic = mqtt_topic

    def get(self):

        code: str = request.args.get("code")
        external_id: str = request.args.get("external_id")

        if code is None or code == "" or external_id is None or external_id == "":
            error = request.args.get("error")
            logger.warning(f"Missing authorization code or external id, error {error}")
            abort(400, message="Missing authorization code or external id")
            return

        message = WeNetAuthentication(external_id, code)
        event = IncomingCustomEvent(self.instance_namespace, message.to_repr(), self.bot_id)
        self.mqtt_publisher.publish_data(self.mqtt_topic, event.to_repr())

        logger.debug("event sent")
        return "OK", 200


class InstanceResourcesBuilder:

    @staticmethod
    def routes(mqtt_publisher: MqttPublishHandler, mqtt_topic: str, instance_namespace: str, bot_id: str):
        return [
            (WeNetMessageInterface, '/message', (mqtt_publisher, mqtt_topic, instance_namespace, bot_id)),
            (WeNetLoginCallbackInterface, '/auth', (mqtt_publisher, mqtt_topic, instance_namespace, bot_id))
        ]
