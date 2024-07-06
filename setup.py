#!/usr/bin/env python3

import os
import subprocess
import sys
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
PYTHON_VERSION = "python3.9"  # Adjust this to your preferred Python version
SERVICE_NAME = "logger_lora"
PROJECT_DIR = "/home/span2node-a/Desktop/Logger_Lora"
VENV_PATH = os.path.join(PROJECT_DIR, '.venv')
MAIN_SCRIPT = os.path.join(PROJECT_DIR, "main.py")

def run_command(command):
    try:
        process = subprocess.run(command, check=True, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return process.stdout.strip()
    except subprocess.CalledProcessError as e:
        logger.error(f"Error executing command: {command}")
        logger.error(f"Error message: {e.stderr}")
        raise

def remove_existing_setup():
    logger.info("Removing existing setup...")
    try:
        run_command(f"sudo systemctl stop {SERVICE_NAME}.service")
        run_command(f"sudo systemctl disable {SERVICE_NAME}.service")
        run_command(f"sudo rm /etc/systemd/system/{SERVICE_NAME}.service")
        run_command("sudo systemctl daemon-reload")
        logger.info("Existing setup removed successfully.")
    except Exception as e:
        logger.warning(f"Error removing existing setup: {e}")

def create_virtual_environment():
    logger.info(f"Creating virtual environment using {PYTHON_VERSION}...")
    run_command(f"{PYTHON_VERSION} -m venv {VENV_PATH}")
    run_command(f"{VENV_PATH}/bin/pip install --upgrade pip")
    run_command(f"{VENV_PATH}/bin/pip install -r {os.path.join(PROJECT_DIR, 'requirements.txt')}")

def create_systemd_service():
    service_content = f"""[Unit]
Description=Logger Lora Data Collection Service
After=multi-user.target

[Service]
ExecStart={VENV_PATH}/bin/python {MAIN_SCRIPT}
WorkingDirectory={PROJECT_DIR}
User=span2node-a
Group=span2node-a
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""

    logger.info("Creating systemd service file...")
    with open(f'/etc/systemd/system/{SERVICE_NAME}.service', 'w') as f:
        f.write(service_content)

def update_main_script():
    logger.info("Updating main.py script...")
    with open(MAIN_SCRIPT, 'r') as f:
        content = f.read()

    if "def wait_for_usb_device" not in content:
        new_content = """import os
import time

def wait_for_usb_device(device_path, timeout=300, check_interval=1):
    start_time = time.time()
    while time.time() - start_time < timeout:
        if os.path.exists(device_path):
            logger.info(f"USB device {device_path} is available")
            return True
        time.sleep(check_interval)
    logger.error(f"Timeout waiting for USB device {device_path}")
    return False

""" + content

        new_content = new_content.replace(
            "datalogger = connect_to_datalogger(config[\"datalogger\"])",
            """# Wait for USB device
            if not wait_for_usb_device(config["datalogger"]["port"]):
                logger.error("USB device not available. Skipping this iteration.")
                continue

            datalogger = connect_to_datalogger(config["datalogger"])"""
        )

        with open(MAIN_SCRIPT, 'w') as f:
            f.write(new_content)

def main():
    if os.geteuid() != 0:
        logger.error("This script must be run with sudo privileges.")
        sys.exit(1)

    remove_existing_setup()
    create_virtual_environment()
    create_systemd_service()
    update_main_script()

    logger.info("Reloading systemd daemon...")
    run_command("sudo systemctl daemon-reload")

    logger.info("Enabling and starting Logger_Lora service...")
    run_command(f"sudo systemctl enable {SERVICE_NAME}.service")
    run_command(f"sudo systemctl start {SERVICE_NAME}.service")

    logger.info("Adding user to dialout group...")
    run_command(f"sudo usermod -a -G dialout span2node-a")

    logger.info("Setup completed successfully.")
    logger.info("Please reboot the system or log out and log back in for group changes to take effect.")
    logger.info(f"The {SERVICE_NAME} service is active and will run on startup.")

if __name__ == "__main__":
    main()