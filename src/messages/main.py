import logging.config
import os

from log_config.logging_config import loggingConfiguration
from messages.ws import MessageInterface
from uhopper.utils.mqtt import MqttPublishHandler

logging.config.dictConfig(loggingConfiguration)
logger = logging.getLogger("uhopper.chatbot.wenet.eattogether.messages")

topic = os.getenv("MQTT_TOPIC")
publisher = MqttPublishHandler(os.getenv("MQTT_HOST"), os.getenv("MQTT_PUBLISHER_ID"), os.getenv("MQTT_USER"),
                               os.getenv("MQTT_PASSWORD"))
instance_namespace = os.getenv("INSTANCE_NAMESPACE")
publisher.connect()

ws = MessageInterface(publisher, topic, instance_namespace, "wenet-eat-together")
bot_messages_app = ws.get_application()

if __name__ == "__main__":
    try:
        ws.run_server()
    except KeyboardInterrupt:
        publisher.disconnect()
