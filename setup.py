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

def run_command(command):
    try:
        process = subprocess.run(command, check=True, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return process.stdout.strip()
    except subprocess.CalledProcessError as e:
        logger.error(f"Error executing command: {command}")
        logger.error(f"Error message: {e.stderr}")
        raise

def check_existing_service():
    try:
        run_command("systemctl is-active logger_lora.service")
        return True
    except subprocess.CalledProcessError:
        return False

def main():
    # Check for root privileges
    if os.geteuid() != 0:
        logger.error("This script must be run with sudo privileges.")
        sys.exit(1)

    # Get the project root directory
    project_root = Path(__file__).parent.absolute()

    # Create virtual environment
    venv_path = project_root / '.venv'
    if not venv_path.exists():
        logger.info(f"Creating virtual environment using {PYTHON_VERSION}...")
        run_command(f"{PYTHON_VERSION} -m venv {venv_path}")
    else:
        logger.info("Virtual environment already exists.")

    # Ensure venv_path exists before proceeding
    if not venv_path.exists():
        logger.error(f"Failed to create virtual environment at {venv_path}. Please check your Python installation.")
        sys.exit(1)

    # Install requirements
    logger.info("Installing requirements...")
    run_command(f"{venv_path}/bin/pip install --upgrade pip")
    run_command(f"{venv_path}/bin/pip install -r {project_root}/requirements.txt")

    # Check if service already exists
    if check_existing_service():
        logger.warning("Logger Lora service already exists. Stopping and disabling existing service...")
        run_command("systemctl stop logger_lora.service")
        run_command("systemctl disable logger_lora.service")

    # Create systemd service file
    service_content = f"""[Unit]
Description=Logger Lora Data Collection Service
After=network.target

[Service]
ExecStart={venv_path}/bin/python {project_root}/main.py
WorkingDirectory={project_root}
User={os.environ.get('SUDO_USER', os.environ.get('USER'))}
Group={os.environ.get('SUDO_USER', os.environ.get('USER'))}
Restart=always
RestartSec=10
Environment="PATH={venv_path}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

[Install]
WantedBy=multi-user.target
"""

    logger.info("Creating systemd service file...")
    with open('/etc/systemd/system/logger_lora.service', 'w') as f:
        f.write(service_content)

    # Create systemd timer file
    timer_content = """[Unit]
Description=Run Logger Lora Data Collection every 30 minutes

[Timer]
OnBootSec=1min
OnUnitActiveSec=30min
AccuracySec=1s

[Install]
WantedBy=timers.target
"""

    logger.info("Creating systemd timer file...")
    with open('/etc/systemd/system/logger_lora.timer', 'w') as f:
        f.write(timer_content)

    # Reload systemd, enable and start the service and timer
    logger.info("Reloading systemd and starting services...")
    run_command("systemctl daemon-reload")
    run_command("systemctl enable logger_lora.service")
    run_command("systemctl enable logger_lora.timer")
    run_command("systemctl start logger_lora.service")
    run_command("systemctl start logger_lora.timer")

    # Verify service and timer status
    logger.info("Verifying service and timer status...")
    service_status = run_command("systemctl is-active logger_lora.service")
    timer_status = run_command("systemctl is-active logger_lora.timer")

    if "active" in service_status and "active" in timer_status:
        logger.info("Setup completed successfully.")
        logger.info("The Logger Lora service is active and will run on startup and every 30 minutes thereafter.")
    else:
        logger.error("Setup completed, but service or timer is not active. Please check system logs for more information.")

if __name__ == "__main__":
    main()