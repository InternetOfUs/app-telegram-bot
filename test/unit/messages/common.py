from unittest import TestCase

from messages.ws import MessageInterface
from test.unit.messages.mock import MockMqttPublishHandler


class CommonTestCase(TestCase):

    def setUp(self) -> None:
        self.mqtt_publisher = MockMqttPublishHandler()
        api = MessageInterface(self.mqtt_publisher, "topic", "namespace", "test", "", "")
        api.get_application().testing = True
        self.client = api.get_application().test_client()
        super().setUp()
