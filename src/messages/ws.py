import logging.config
import os

from flask import Flask, request

from log_config.logging_config import loggingConfiguration
from messages.models import Message, TextualMessage, TaskNotification, TaskConcludedNotification, \
    TaskVolunteerNotification, TaskProposalNotification, MessageFromUserNotification

logging.config.dictConfig(loggingConfiguration)
logger = logging.getLogger("tapoi.api")

app = Flask(__name__)
host = os.getenv("MESSAGES_HOST", "0.0.0.0")
port = os.getenv("MESSAGES_PORT", "12345")


@app.route('/message', methods=['POST'])
def receive_message():
    data = request.get_json()
    try:
        message_type = data["type"]
        if message_type == Message.TYPE_TEXTUAL_MESSAGE:
            message = TextualMessage.from_repr(data)

        elif message_type == Message.TYPE_TASK_NOTIFICATION:
            notification_type = data["notification_type"]
            if notification_type == TaskNotification.NOTIFICATION_TYPE_CONCLUDED:
                message = TaskConcludedNotification.from_repr(data)
            elif notification_type == TaskNotification.NOTIFICATION_TYPE_VOLUNTEER:
                message = TaskVolunteerNotification.from_repr(data)
            elif notification_type == TaskNotification.NOTIFICATION_TYPE_PROPOSAL:
                message = TaskProposalNotification.from_repr(data)
            elif notification_type == TaskNotification.NOTIFICATION_TYPE_MESSAGE_FROM_USER:
                message = MessageFromUserNotification.from_repr(data)
            else:
                return {"Error": "Unrecognized type [%s] of notification type" % notification_type}, 400
        else:
            return {"Error": "Unrecognized type [%s] of message" % message_type}, 400
        # TODO: do something with the message
        print(message.to_repr())
        return {}, 200
    except KeyError:
        return {"Error": "One or more required keys are missing"}, 400
    except ValueError:
        return {"Error": "One or more values of the enum fields are not respected. Please check the documentation and "
                         "try again"}, 400


if __name__ == "__main__":
    app.run(host=host, port=port)
