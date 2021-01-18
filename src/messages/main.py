import logging.config
import os
import uuid

from common.logging_config import get_logging_configuration
from messages.ws import MessageInterface
from uhopper.utils.mqtt import MqttPublishHandler

bot_id = os.getenv("BOT_ID")

logging.config.dictConfig(get_logging_configuration(f"{bot_id}-messages"))
logger = logging.getLogger("uhopper.chatbot.wenet.messages")

topic = os.getenv("MQTT_TOPIC")
publisher = MqttPublishHandler(
    os.getenv("MQTT_HOST"),
    f"{os.getenv('MQTT_PUBLISHER_ID')}_{uuid.uuid4()}",
    os.getenv("MQTT_USER"),
    os.getenv("MQTT_PASSWORD")
)
instance_namespace = os.getenv("INSTANCE_NAMESPACE")
app_id = os.getenv("WENET_APP_ID")
hub_url = os.getenv("WENET_HUB_URL")
oauth_success_url = f"{hub_url}/oauth/complete"

publisher.connect()

ws = MessageInterface(publisher, topic, instance_namespace, bot_id, app_id, oauth_success_url)
bot_messages_app = ws.get_application()

host = os.getenv("MESSAGES_HOST", "0.0.0.0")
port = int(os.getenv("MESSAGES_PORT", "12345"))

if __name__ == "__main__":
    try:
        ws.run(host, port)
    except KeyboardInterrupt:
        publisher.disconnect()
