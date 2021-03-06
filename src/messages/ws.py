import logging

from flask import Flask
from flask_restful import Api

from messages.instance import InstanceResourcesBuilder
from uhopper.utils.mqtt.handler import MqttPublishHandler


class MessageInterface:

    def __init__(self,
                 mqtt_publisher: MqttPublishHandler,
                 mqtt_topic: str,
                 instance_namespace: str,
                 bot_id: str,
                 wenet_app_id: str,
                 oauth_successful_redirect_url: str
                 ) -> None:
        self.mqtt_publisher = mqtt_publisher
        self.mqtt_topic = mqtt_topic
        self.instance_namespace = instance_namespace
        self.bot_id = bot_id
        self._app_id = wenet_app_id
        self._oauth_successful_redirect_url = oauth_successful_redirect_url
        self._app = Flask("chatbot-interface-ws")
        self._api = Api(app=self._app)
        self._init_resources()

    def _init_resources(self) -> None:
        for resource, path, args in InstanceResourcesBuilder.routes(
                self.mqtt_publisher,
                self.mqtt_topic,
                self.instance_namespace,
                self.bot_id,
                self._app_id,
                self._oauth_successful_redirect_url
        ):
            logging.debug("Installing route %s", path)
            self._api.add_resource(resource, path, resource_class_args=args)

    def run(self, host: str, port: int):
        self._app.run(host=host, port=port, debug=False)

    def get_application(self):
        return self._app
