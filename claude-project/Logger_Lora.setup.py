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
        run_command(f"sudo systemctl stop {SERVICE_NAME}.timer")
        run_command(f"sudo systemctl disable {SERVICE_NAME}.timer")
        run_command(f"sudo rm /etc/systemd/system/{SERVICE_NAME}.service")
        run_command(f"sudo rm /etc/systemd/system/{SERVICE_NAME}.timer")
        run_command("sudo systemctl daemon-reload")
        logger.info("Existing setup removed successfully.")
    except Exception as e:
        logger.warning(f"Error removing existing setup: {e}")

def main():
    if os.geteuid() != 0:
        logger.error("This script must be run with sudo privileges.")
        sys.exit(1)

    remove_existing_setup()

    project_root = Path(__file__).parent.absolute()
    venv_path = project_root / '.venv'

    if not venv_path.exists():
        logger.info(f"Creating virtual environment using {PYTHON_VERSION}...")
        run_command(f"{PYTHON_VERSION} -m venv {venv_path}")
    else:
        logger.info("Virtual environment already exists.")

    if not venv_path.exists():
        logger.error(f"Failed to create virtual environment at {venv_path}. Please check your Python installation.")
        sys.exit(1)

    logger.info("Installing requirements...")
    run_command(f"{venv_path}/bin/pip install --upgrade pip")
    run_command(f"{venv_path}/bin/pip install -r {project_root}/requirements.txt")

    service_content = f"""[Unit]
Description=Logger Lora Data Collection Service
After=network.target

[Service]
ExecStart={venv_path}/bin/python {project_root}/main.py
WorkingDirectory={project_root}
User={os.environ.get('SUDO_USER', os.environ.get('USER'))}
Group={os.environ.get('SUDO_USER', os.environ.get('USER'))}
Restart=on-failure
RestartSec=60
StartLimitIntervalSec=300
StartLimitBurst=3
Environment="PATH={venv_path}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

[Install]
WantedBy=multi-user.target
"""

    logger.info("Creating systemd service file...")
    with open(f'/etc/systemd/system/{SERVICE_NAME}.service', 'w') as f:
        f.write(service_content)

    timer_content = f"""[Unit]
Description=Run Logger Lora Data Collection every 30 minutes

[Timer]
OnBootSec=1min
OnUnitActiveSec=30min
AccuracySec=1s

[Install]
WantedBy=timers.target
"""

    logger.info("Creating systemd timer file...")
    with open(f'/etc/systemd/system/{SERVICE_NAME}.timer', 'w') as f:
        f.write(timer_content)

    logger.info("Reloading systemd and starting services...")
    run_command("systemctl daemon-reload")
    run_command(f"systemctl enable {SERVICE_NAME}.service")
    run_command(f"systemctl enable {SERVICE_NAME}.timer")
    run_command(f"systemctl start {SERVICE_NAME}.service")
    run_command(f"systemctl start {SERVICE_NAME}.timer")

    logger.info("Adding user to dialout group...")
    run_command(f"usermod -a -G dialout {os.environ.get('SUDO_USER', os.environ.get('USER'))}")

    logger.info("Setup completed successfully.")
    logger.info("Please reboot the system or log out and log back in for group changes to take effect.")
    logger.info(f"The {SERVICE_NAME} service is active and will run on startup and every 30 minutes thereafter.")

if __name__ == "__main__":
    main()
