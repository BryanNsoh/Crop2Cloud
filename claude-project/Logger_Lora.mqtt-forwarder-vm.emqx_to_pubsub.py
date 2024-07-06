import sys
import traceback

# Immediate error logging
try:
    import logging
    logging.basicConfig(filename='/home/bnsoh652/app.log', level=logging.DEBUG,
                        format='%(asctime)s - %(levelname)s - %(message)s')
    logging.info("Script started")
except Exception as e:
    with open('/home/bnsoh652/script_error.log', 'w') as f:
        f.write(f"Error setting up logging: {str(e)}\n")
        f.write(traceback.format_exc())
    sys.exit(1)

import base64
import json
import os
import time
import ssl
from logging.handlers import RotatingFileHandler
from google.cloud import pubsub_v1
import paho.mqtt.client as mqtt
import yaml

# EMQX Cloud connection details
EMQX_HOST = 's11a17e5.ala.us-east-1.emqxsl.com'
EMQX_PORT = 8883
EMQX_TOPIC = 'device/data/uplink'
EMQX_USERNAME = 'admin'
EMQX_PASSWORD = 'Iam>Than1M'
CA_CERT_PATH = os.path.expanduser('~/emqxsl-ca.crt')

# Google Cloud Pub/Sub Configuration
PROJECT_ID = 'crop2cloud24'
TOPIC_ID = 'tester'
MAX_RETRIES = 3
RETRY_DELAY = 5

# Logging configuration
LOG_FILENAME = os.path.expanduser('~/app.log')
LOG_MAX_SIZE = 10 * 1024 * 1024  # 10 MB
LOG_BACKUP_COUNT = 5

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Create a rotating file handler
handler = RotatingFileHandler(LOG_FILENAME, maxBytes=LOG_MAX_SIZE, backupCount=LOG_BACKUP_COUNT)
handler.setLevel(logging.DEBUG)

# Create a formatter and add it to the handler
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

# Add the handler to the logger
logger.addHandler(handler)

# Load sensor mapping
def load_sensor_mapping():
    try:
        with open(os.path.expanduser('~/sensor_mapping.yaml'), 'r') as f:
            mapping = yaml.safe_load(f)
        return mapping
    except Exception as e:
        logger.error(f"Error loading sensor mapping: {str(e)}")
        return None

SENSOR_MAPPING = load_sensor_mapping()

def get_sensor_info(hash_value):
    for sensor in SENSOR_MAPPING:
        if sensor['hash'] == hash_value:
            logger.debug(f"Found sensor info for hash {hash_value}: {json.dumps(sensor)}")
            return sensor
    logger.warning(f"No sensor info found for hash {hash_value}")
    return None

def prepare_pubsub_messages(decoded_payload, device_name, timestamp):
    logger.info(f"Preparing Pub/Sub messages for device {device_name} at {timestamp}")
    logger.debug(f"Decoded payload: {json.dumps(decoded_payload)}")
    messages = []
    for hash_value, value in decoded_payload.items():
        if hash_value != 'time':  # Skip the 'time' field
            sensor_info = get_sensor_info(hash_value)
            if sensor_info:
                message = {
                    "timestamp": timestamp,
                    "sensor_id": sensor_info['sensor_id'],
                    "value": value,
                    "project_name": PROJECT_ID,
                    "dataset_name": f"{sensor_info['field']}_trt{sensor_info['treatment']}",
                    "table_name": f"plot_{sensor_info['plot_number']}"
                }
                logger.debug(f"Prepared message: {json.dumps(message)}")
                messages.append(message)
            else:
                logger.warning(f"No mapping found for hash: {hash_value}")
    logger.info(f"Prepared {len(messages)} messages for Pub/Sub")
    return messages

def process_message(message):
    """
    Process the received MQTT message.

    Args:
        message (mqtt.MQTTMessage): The received MQTT message.
    """
    try:
        logger.info("Processing new MQTT message")
        logger.debug(f"Raw MQTT message: {message.payload}")
        
        decoded_message = json.loads(message.payload.decode("utf-8"))
        logger.info(f"Decoded MQTT message: {json.dumps(decoded_message, indent=2)}")

        # Extract and decode the base64 payload
        payload = decoded_message['data']
        logger.debug(f"Base64 payload: {payload}")
        
        decoded_payload = json.loads(base64.b64decode(payload).decode('utf-8'))
        logger.info(f"Decoded payload: {json.dumps(decoded_payload, indent=2)}")

        # Prepare messages for Pub/Sub
        device_name = decoded_message['deviceName']
        timestamp = decoded_message['time']
        pubsub_messages = prepare_pubsub_messages(decoded_payload, device_name, timestamp)

        # Publish messages to Pub/Sub
        for msg in pubsub_messages:
            publish_to_pubsub(msg)

    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        logger.exception("Full traceback:")

def publish_to_pubsub(data, retry_count=0):
    """
    Publish data to Google Cloud Pub/Sub using default credentials.

    Args:
        data (dict): The data to publish to Pub/Sub.
        retry_count (int): The current retry count.
    """
    try:
        logger.info("Attempting to publish message to Pub/Sub")
        logger.debug(f"Message data: {json.dumps(data, indent=2)}")
        
        publisher = pubsub_v1.PublisherClient()
        topic_path = publisher.topic_path(PROJECT_ID, TOPIC_ID)
        data_str = json.dumps(data)
        future = publisher.publish(topic_path, data=data_str.encode('utf-8'))
        message_id = future.result()  # Wait for the publish to complete
        logger.info(f"Successfully published message with ID: {message_id}")
        logger.debug(f"Published data: {data_str}")
    except Exception as e:
        logger.error(f"Error publishing to Pub/Sub: {str(e)}")
        logger.error(f"Failed data: {json.dumps(data, indent=2)}")
        if retry_count < MAX_RETRIES:
            logger.info(f"Retrying in {RETRY_DELAY} seconds... (Attempt {retry_count + 1}/{MAX_RETRIES})")
            time.sleep(RETRY_DELAY)
            publish_to_pubsub(data, retry_count + 1)
        else:
            logger.error("Max retries reached. Skipping message.")

def on_connect(client, userdata, flags, rc):
    """
    Callback function for MQTT client connection.

    Args:
        client (mqtt.Client): The MQTT client instance.
        userdata (Any): User-defined data passed to the callback.
        flags (dict): Response flags from the broker.
        rc (int): Connection result code.
    """
    if rc == 0:
        logger.info("Successfully connected to EMQX Cloud")
        client.subscribe(EMQX_TOPIC)
        logger.info(f"Subscribed to topic: {EMQX_TOPIC}")
    else:
        logger.error(f"Failed to connect to EMQX Cloud, return code {rc}")

def on_message(client, userdata, message):
    """
    Callback function for MQTT message reception.

    Args:
        client (mqtt.Client): The MQTT client instance.
        userdata (Any): User-defined data passed to the callback.
        message (mqtt.MQTTMessage): The received MQTT message.
    """
    logger.info(f"Received new message on topic: {message.topic}")
    process_message(message)

def main():
    client = mqtt.Client(protocol=mqtt.MQTTv311)
    client.username_pw_set(EMQX_USERNAME, EMQX_PASSWORD)
    client.tls_set(ca_certs=CA_CERT_PATH, tls_version=ssl.PROTOCOL_TLSv1_2)
    client.on_connect = on_connect
    client.on_message = on_message
    
    logger.info(f"Attempting to connect to EMQX Cloud at {EMQX_HOST}:{EMQX_PORT}...")
    try:
        client.connect(EMQX_HOST, EMQX_PORT)
        logger.info("Connection successful. Starting MQTT client loop...")
        client.loop_forever()
    except Exception as e:
        logger.error(f"Failed to connect to EMQX Cloud: {str(e)}")
        logger.exception("Full traceback:")

if __name__ == "__main__":
    logger.info("Starting EMQX to Pub/Sub Bridge")
    main()