import json
from unittest.mock import Mock

from test.unit.messages.common import CommonTestCase


class TestEndpoint(CommonTestCase):

    def test_parsing_volunteer_notification(self):
        self.setUp()
        mock_publish = Mock()
        self.mqtt_publisher.publish_data = mock_publish
        raw_input = {
            "appId": 1,
            "communityId": "",
            "label": "TaskVolunteerNotification",
            "receiverId": "1",
            "taskId": "5f773c9e34a5436bf1321ef0",
            "attributes": {
                "volunteerId": 4
            }
        }
        result = self.client.post('/message', data=json.dumps(raw_input), content_type='application/json')
        self.assertEqual(result.status_code, 200)
        mock_publish.assert_called_once()

    def test_invalid_message(self):
        self.setUp()
        mock_publish = Mock()
        self.mqtt_publisher.publish_data = mock_publish
        raw_input = {
            "app": 1,
            "communityId": "",
            "label": "taskProposal",
            "receiverId": "1",
            "taskId": "5f773c9e34a5436bf1321ef0",
            "notificationType": "TaskVolunteerNotification",
            "attributes": {
                "volunteerId": 4
            }
        }
        result = self.client.post('/message', data=json.dumps(raw_input), content_type='application/json')
        self.assertEqual(result.status_code, 400)
        mock_publish.assert_not_called()

    def test_parsing_proposal_notification(self):
        self.setUp()
        mock_publish = Mock()
        self.mqtt_publisher.publish_data = mock_publish
        raw_input = {
            "appId": 1,
            "communityId": "",
            "label": "TaskProposalNotification",
            "receiverId": "1",
            "taskId": "5f773c9e34a5436bf1321ef0",
            "attributes": {}
        }
        result = self.client.post('/message', data=json.dumps(raw_input), content_type='application/json')
        self.assertEqual(result.status_code, 200)
        mock_publish.assert_called_once()

    def test_parsing_selection_notification(self):
        self.setUp()
        mock_publish = Mock()
        self.mqtt_publisher.publish_data = mock_publish
        raw_input = {
            "appId": 1,
            "communityId": "",
            "label": "TaskSelectionNotification",
            "receiverId": "1",
            "taskId": "5f773c9e34a5436bf1321ef0",
            "attributes": {
                "outcome": "accepted"
            }
        }
        result = self.client.post('/message', data=json.dumps(raw_input), content_type='application/json')
        self.assertEqual(result.status_code, 200)
        mock_publish.assert_called_once()

    def test_parsing_conclude_notification(self):
        self.setUp()
        mock_publish = Mock()
        self.mqtt_publisher.publish_data = mock_publish
        raw_input = {
            "appId": 1,
            "communityId": "",
            "label": "TaskConcludedNotification",
            "receiverId": "1",
            "taskId": "5f773c9e34a5436bf1321ef0",
            "attributes": {
                "outcome": "completed"
            }
        }
        result = self.client.post('/message', data=json.dumps(raw_input), content_type='application/json')
        self.assertEqual(result.status_code, 200)
        mock_publish.assert_called_once()

    def test_parsing_textual_message(self):
        self.setUp()
        mock_publish = Mock()
        self.mqtt_publisher.publish_data = mock_publish
        raw_input = {
            "appId": 1,
            "communityId": "",
            "label": "TextualMessage",
            "receiverId": "1",
            "taskId": "5f773c9e34a5436bf1321ef0",
            "attributes": {
                "title": "title",
                "text": "text"
            }
        }
        result = self.client.post('/message', data=json.dumps(raw_input), content_type='application/json')
        self.assertEqual(result.status_code, 200)
        mock_publish.assert_called_once()
