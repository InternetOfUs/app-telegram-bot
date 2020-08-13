import logging.config
import os
import uuid

from log_config.logging_config import loggingConfiguration
from messages.ws import MessageInterface
from uhopper.utils.mqtt import MqttPublishHandler

logging.config.dictConfig(loggingConfiguration)
logger = logging.getLogger("uhopper.chatbot.wenet.eattogether.messages")

topic = os.getenv("MQTT_TOPIC")
publisher = MqttPublishHandler(
    os.getenv("MQTT_HOST"),
    f"{os.getenv('MQTT_PUBLISHER_ID')}_{uuid.uuid4()}",
    os.getenv("MQTT_USER"),
    os.getenv("MQTT_PASSWORD")
)
instance_namespace = os.getenv("INSTANCE_NAMESPACE")
publisher.connect()

ws = MessageInterface(publisher, topic, instance_namespace, "wenet-eat-together")
bot_messages_app = ws.get_application()

host = os.getenv("MESSAGES_HOST", "0.0.0.0")
port = int(os.getenv("MESSAGES_PORT", "12345"))

if __name__ == "__main__":
    try:
        ws.run(host, port)
    except KeyboardInterrupt:
        publisher.disconnect()
