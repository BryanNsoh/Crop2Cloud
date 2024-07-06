#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Update system and install dependencies
sudo apt update
sudo apt install -y python3 python3-pip python3-venv

# Install Google Cloud SDK
if ! command -v gcloud &> /dev/null; then
    echo "Installing Google Cloud SDK..."
    echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
    curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key --keyring /usr/share/keyrings/cloud.google.gpg add -
    sudo apt-get update && sudo apt-get install -y google-cloud-sdk
else
    echo "Google Cloud SDK is already installed."
fi

# Create a virtual environment and activate it
python3 -m venv $HOME/venv
source $HOME/venv/bin/activate

# Install Python packages
pip install google-cloud-pubsub==2.21.5 paho-mqtt==2.1.0 pyyaml

# Ensure the CA certificate file is readable
if [ -f "$HOME/emqxsl-ca.crt" ]; then
    sudo chmod 644 $HOME/emqxsl-ca.crt
else
    echo "Warning: emqxsl-ca.crt not found in the home directory."
fi

# Set appropriate permissions for the Python script
chmod +x $HOME/emqx_to_pubsub.py

# Create a systemd service file
sudo tee /etc/systemd/system/emqx_to_pubsub.service > /dev/null <<EOT
[Unit]
Description=EMQX to Pub/Sub Bridge
After=network.target

[Service]
ExecStart=$HOME/venv/bin/python $HOME/emqx_to_pubsub.py
Restart=always
RestartSec=5
User=$USER
WorkingDirectory=$HOME
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOT

# Reload systemd, enable and start the service
sudo systemctl daemon-reload
sudo systemctl enable emqx_to_pubsub.service
sudo systemctl start emqx_to_pubsub.service

# Print final instructions
echo "Setup complete. You can check the service status with:"
echo "sudo systemctl status emqx_to_pubsub.service"
echo "And view the logs with:"
echo "tail -f $HOME/app.log"

echo "Please ensure that the sensor_mapping.yaml file is present in your home directory."
echo "If you need to make any changes, edit the $HOME/emqx_to_pubsub.py file and restart the service with:"
echo "sudo systemctl restart emqx_to_pubsub.service"