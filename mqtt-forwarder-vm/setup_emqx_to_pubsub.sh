#!/bin/bash

# Update your system's package list
sudo apt update

# Install NTPsec and utilities for setting timezone if not already installed
sudo apt install -y ntpsec tzdata

# Set the timezone to US Central
sudo timedatectl set-timezone America/Chicago

# Enable and start the NTPsec service to synchronize the clock
sudo systemctl enable ntpsec
sudo systemctl start ntpsec

# Check the status of the NTPsec service
sudo systemctl status ntpsec

# Optional: Show the current date and time to verify
date

# Install necessary packages
sudo apt install -y python3 python3-pip python3-venv

# Set environment variable for Google Cloud Credentials and add it to bashrc for persistence
export GOOGLE_APPLICATION_CREDENTIALS="$HOME/crop2cloud24-4b30f843e1cf.json"
echo "export GOOGLE_APPLICATION_CREDENTIALS=\"$GOOGLE_APPLICATION_CREDENTIALS\"" >> ~/.bashrc

# Authenticate using the service account
gcloud auth activate-service-account --key-file=$GOOGLE_APPLICATION_CREDENTIALS

# Clean up duplicate entries in google-cloud-sdk.list
sudo sed -i '/^deb/!d' /etc/apt/sources.list.d/google-cloud-sdk.list
sudo apt-get update

# Install Google Cloud SDK
echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee /etc/apt/sources.list.d/google-cloud-sdk.list
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key --keyring /usr/share/keyrings/cloud.google.gpg add -
sudo apt-get update && sudo apt-get install -y google-cloud-sdk

# Create a virtual environment and activate it
python3 -m venv venv
source venv/bin/activate

# Install Python packages
pip install google-cloud-pubsub==2.21.5 paho-mqtt==2.1.0

# Make sure the CA certificate file is readable
sudo chmod 644 $HOME/emqxsl-ca.crt

# Create the Python script file with the updated code
cat > $HOME/emqx_to_pubsub.py <<EOL
import base64
import json
import os
import time
import ssl
import logging
from logging.handlers import RotatingFileHandler
from google.cloud.pubsub_v1 import PublisherClient
import paho.mqtt.client as mqtt

# EMQX Cloud connection details
EMQX_HOST = 's11a17e5.ala.us-east-1.emqxsl.com'
EMQX_PORT = 8883
EMQX_TOPIC = 'device/data/uplink'
EMQX_USERNAME = 'admin'
EMQX_PASSWORD = 'Iam>Than1M'
CA_CERT_PATH = os.path.expanduser('~/emqxsl-ca.crt')  # Use expanduser to ensure correct path

# Google Cloud Pub/Sub Configuration
PROJECT_ID = 'crop2cloud24'
TOPIC_ID = 'projects/crop2cloud24/topics/tester'
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

# Pub/Sub client setup
publisher = PublisherClient()
topic_path = publisher.topic_path(PROJECT_ID, TOPIC_ID)

def process_message(message):
    """
    Process the received MQTT message.

    Args:
        message (mqtt.MQTTMessage): The received MQTT message.
    """
    try:
        decoded_message = str(message.payload.decode("utf-8"))
        json_data = json.loads(decoded_message)
        logger.info(f"Decoded JSON data: {json_data}")
        publish_to_pubsub(json_data)
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")

def publish_to_pubsub(data, retry_count=0):
    """
    Publish data to Google Cloud Pub/Sub.

    Args:
        data (dict): The data to publish to Pub/Sub.
        retry_count (int): The current retry count.
    """
    try:
        data_str = json.dumps(data)
        publisher.publish(topic_path, data=data_str.encode('utf-8'))
        logger.info("Published data to Pub/Sub")
    except Exception as e:
        logger.error(f"Error publishing to Pub/Sub: {str(e)}")
        if retry_count < MAX_RETRIES:
            logger.info(f"Retrying in {RETRY_DELAY} seconds...")
            time.sleep(RETRY_DELAY)
            publish_to_pubsub(data, retry_count + 1)
        else:
            logger.warning("Max retries reached. Skipping message.")

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
        logger.info("Connected to EMQX Cloud")
        client.subscribe(EMQX_TOPIC)
        logger.info(f"Subscribed to topic: {EMQX_TOPIC}")
    else:
        logger.error(f"Failed to connect, return code {rc}")

def on_message(client, userdata, message):
    """
    Callback function for MQTT message reception.

    Args:
        client (mqtt.Client): The MQTT client instance.
        userdata (Any): User-defined data passed to the callback.
        message (mqtt.MQTTMessage): The received MQTT message.
    """
    logger.info(f"Received message on topic: {message.topic}")
    process_message(message)

def main():
    client = mqtt.Client(protocol=mqtt.MQTTv311)
    client.username_pw_set(EMQX_USERNAME, EMQX_PASSWORD)
    client.tls_set(ca_certs=CA_CERT_PATH, tls_version=ssl.PROTOCOL_TLSv1_2)
    client.on_connect = on_connect
    client.on_message = on_message
    
    logger.info(f"Connecting to EMQX Cloud at {EMQX_HOST}:{EMQX_PORT}...")
    client.connect(EMQX_HOST, EMQX_PORT)
    
    logger.info("Starting MQTT client loop...")
    client.loop_forever()

if __name__ == "__main__":
    main()
EOL

# Set the appropriate permissions for the Python script
chmod +x $HOME/emqx_to_pubsub.py

# Create a systemd service file for the Python script
sudo tee /etc/systemd/system/emqx_to_pubsub.service > /dev/null <<EOT
[Unit]
Description=EMQX to Pub/Sub Bridge
After=network.target

[Service]
ExecStart=/bin/bash -c 'source $HOME/venv/bin/activate && python $HOME/emqx_to_pubsub.py'
Restart=always
RestartSec=5
User=$USER
WorkingDirectory=$HOME

[Install]
WantedBy=multi-user.target
EOT

# Reload systemd and start the service
sudo systemctl daemon-reload
sudo systemctl enable emqx_to_pubsub.service
sudo systemctl start emqx_to_pubsub.service

# Print final instructions
echo "Setup complete. You can check the service status with:"
echo "sudo systemctl status emqx_to_pubsub.service"
echo "And view the logs with:"
echo "cat $HOME/app.log"