import paho.mqtt.client as mqtt
from google.cloud import pubsub_v1
import json
import os

# MQTT configuration
mqtt_broker = "4c505e41f8014e6bbdc1f56a498c7c2d.s1.eu.hivemq.cloud"
mqtt_port = 8883
mqtt_topic = "/linovision/uplink/#"
mqtt_username = "bnsoh2"
mqtt_password = "Iam>Than1M"

# Google Cloud configuration
project_id = "crop2cloud24"
pubsub_topic = "projects/crop2cloud24/topics/tester"

publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(project_id, pubsub_topic)

def on_connect(client, userdata, flags, rc):
    print(f"Connected with result code {rc}")
    client.subscribe(mqtt_topic)

def on_message(client, userdata, msg):
    try:
        print(f"Received message on topic {msg.topic}: {msg.payload}")
        future = publisher.publish(topic_path, data=msg.payload)
        print(f"Published message to {topic_path}")
    except Exception as e:
        print(f"Error publishing to Pub/Sub: {e}")

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

# Set up TLS for MQTT
client.tls_set()

# Set username and password
client.username_pw_set(mqtt_username, mqtt_password)

client.connect(mqtt_broker, mqtt_port, 60)
client.loop_forever()