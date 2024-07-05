#!/bin/bash

# Exit on any error
set -e

# Update and install dependencies
sudo apt-get update
sudo apt-get install -y python3-venv python3-pip

# Create a virtual environment
python3 -m venv ~/mqtt_bridge_venv

# Activate the virtual environment
source ~/mqtt_bridge_venv/bin/activate

# Install Python dependencies in the virtual environment
pip install paho-mqtt google-cloud-pubsub

# Create MQTT bridge directory
mkdir -p ~/mqtt_bridge
cd ~/mqtt_bridge

# Copy the Python script
cp ~/mqtt_to_pubsub.py .

# Create systemd service file
sudo tee /etc/systemd/system/mqtt-bridge.service > /dev/null << EOL
[Unit]
Description=MQTT to Pub/Sub Bridge
After=network.target

[Service]
ExecStart=/home/$USER/mqtt_bridge_venv/bin/python3 /home/$USER/mqtt_bridge/mqtt_to_pubsub.py
WorkingDirectory=/home/$USER/mqtt_bridge
User=$USER
Restart=always
RestartSec=10
Environment="GOOGLE_APPLICATION_CREDENTIALS=/home/$USER/crop2cloud24-4b30f843e1cf.json"

[Install]
WantedBy=multi-user.target
EOL

# Enable and start the service
sudo systemctl enable mqtt-bridge.service
sudo systemctl start mqtt-bridge.service

echo "Setup complete. MQTT bridge is now running as a service."
echo "To view logs, use: sudo journalctl -u mqtt-bridge -f"