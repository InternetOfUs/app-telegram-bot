import json
from unittest.mock import Mock

from test.test_messages.common import CommonTestCase
from wenet.common.model.message.message import TaskNotification, TextualMessage


class TestEndpoint(CommonTestCase):
    def test_valid_notification(self):
        self.setUp()
        mock_publish = Mock()
        self.mqtt_publisher.publish_data = mock_publish
        raw_input = {
            "type": "taskNotification",
            "recipientId": "qwerty",
            "title": "qwerty",
            "text": "qwerty",
            "notificationType": "taskProposal",
            "description": "qwerty",
            "taskId": "puppa"
        }
        result = self.client.post('/message', data=json.dumps(raw_input), content_type='application/json')
        self.assertEqual(result.status_code, 200)
        mock_publish.assert_called_once()

    def test_invalid_message_type(self):
        self.setUp()
        mock_publish = Mock()
        self.mqtt_publisher.publish_data = mock_publish
        raw_input = {
            "type": "randomType",
            "recipientId": "qwerty",
            "title": "qwerty",
            "text": "qwerty",
            "notificationType": "taskProposal",
            "description": "qwerty",
            "taskId": "puppa"
        }
        result = self.client.post('/message', data=json.dumps(raw_input), content_type='application/json')
        self.assertEqual(result.status_code, 400)
        mock_publish.assert_not_called()

    def test_invalid_notification_type(self):
        self.setUp()
        mock_publish = Mock()
        self.mqtt_publisher.publish_data = mock_publish
        raw_input = {
            "type": TaskNotification.TYPE,
            "recipientId": "qwerty",
            "title": "qwerty",
            "text": "qwerty",
            "notificationType": "random",
            "description": "qwerty",
            "taskId": "puppa"
        }
        result = self.client.post('/message', data=json.dumps(raw_input), content_type='application/json')
        self.assertEqual(result.status_code, 400)
        mock_publish.assert_not_called()

    def test_valid_message(self):
        self.setUp()
        mock_publish = Mock()
        self.mqtt_publisher.publish_data = mock_publish
        raw_input = {
            "type": TextualMessage.TYPE,
            "recipientId": "qwerty",
            "title": "qwerty",
            "text": "qwerty"
        }
        result = self.client.post('/message', data=json.dumps(raw_input), content_type='application/json')
        self.assertEqual(result.status_code, 200)
        mock_publish.assert_called_once()
