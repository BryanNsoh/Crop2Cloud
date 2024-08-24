import os
import subprocess
import shutil
from pathlib import Path
import sys
import json
from datetime import datetime
import logging

def setup_logger(name, log_file, level='INFO'):
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    
    return logger

logger = setup_logger("setup", "setup.log")

def run_command(command, continue_on_error=False):
    logger.debug(f"Running Command: {command}")
    result = subprocess.run(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True
    )

    if result.returncode != 0:
        logger.error(f"Error running command '{command}': {result.stderr}")
        if not continue_on_error:
            exit(1)

    return result.stdout, result.stderr

def create_file(file_name, content):
    with open(file_name, "w") as f:
        f.write(content)
    logger.info(f"Created file: {file_name}")
    return file_name

def enable_and_start_systemd(unit_name):
    logger.info(f"Enabling and starting systemd unit: {unit_name}")
    run_command(f"sudo systemctl enable {unit_name}", continue_on_error=True)
    run_command(f"sudo systemctl start {unit_name}", continue_on_error=True)

def install_required_packages():
    logger.info("Installing required packages")
    packages = ["python3-venv", "python3-pip", "python3-yaml", "python3-serial", "git"]
    run_command(f"sudo apt-get update && sudo apt-get install -y {' '.join(packages)}")

def rebuild_venv_if_needed():
    venv_path = os.path.join(os.getcwd(), ".venv")
    if not os.path.exists(venv_path) or sys.prefix != venv_path:
        logger.info("Rebuilding virtual environment")
        run_command(f"python3 -m venv {venv_path}")
        run_command(f"{venv_path}/bin/pip install -r requirements.txt")
        run_command(f"{venv_path}/bin/pip install --upgrade rak811")

def setup_reboot_counter():
    logger.info("Setting up reboot counter")
    counter_path = os.path.join(os.getcwd(), 'logs', 'reboot_counter.json')
    os.makedirs(os.path.dirname(counter_path), exist_ok=True)
    if not os.path.exists(counter_path):
        with open(counter_path, 'w') as f:
            json.dump({'count': 0, 'last_reset': datetime.now().isoformat()}, f)
    logger.info("Reboot counter setup complete")

def load_config():
    try:
        import yaml
    except ImportError:
        logger.error("YAML module not found. Installing required packages.")
        install_required_packages()
        import yaml

    with open("config/config.yaml", "r") as f:
        return yaml.safe_load(f)

def setup_systemd_reboot_service():
    logger.info("Setting up systemd reboot service")
    
    reboot_service_content = """
[Unit]
Description=Reboot service for Logger_Lora

[Service]
Type=oneshot
ExecStart=/sbin/reboot
"""
    
    reboot_path_content = """
[Path]
PathExists=/tmp/logger_reboot_trigger

[Install]
WantedBy=multi-user.target
"""
    
    create_file("/etc/systemd/system/logger-reboot.service", reboot_service_content)
    create_file("/etc/systemd/system/logger-reboot.path", reboot_path_content)
    
    run_command("sudo systemctl daemon-reload")
    enable_and_start_systemd("logger-reboot.path")
    
    logger.info("Systemd reboot service setup complete")

def setup_lora_phat():
    logger.info("Starting LoRa pHAT setup...")

    # Configure UART
    logger.info("Configuring UART...")
    config_file = "/boot/config.txt"
    with open(config_file, "r") as f:
        config_content = f.read()
    
    if "enable_uart=1" not in config_content:
        with open(config_file, "a") as f:
            f.write("\nenable_uart=1\n")
    
    if "dtoverlay=disable-bt" not in config_content:
        with open(config_file, "a") as f:
            f.write("dtoverlay=disable-bt\n")

    # Stop, disable, and mask serial-getty service
    logger.info("Stopping and disabling serial-getty service...")
    run_command("sudo systemctl stop serial-getty@ttyAMA0.service")
    run_command("sudo systemctl disable serial-getty@ttyAMA0.service")
    run_command("sudo systemctl mask serial-getty@ttyAMA0.service")

    # Set up udev rule for LoRa pHAT
    logger.info("Setting up udev rule for LoRa pHAT...")
    udev_rule = 'KERNEL=="ttyAMA0", GROUP="dialout", MODE="0660"'
    create_file("/etc/udev/rules.d/99-lora-phat.rules", udev_rule)

    logger.info("LoRa pHAT setup complete")

def main():
    logger.info("Starting setup process")

    # Check if running as root
    if os.geteuid() != 0:
        logger.error("This script must be run as root. Please use sudo.")
        exit(1)

    # Install required packages
    install_required_packages()

    # Set your project path
    project_path = os.getcwd()
    logger.info(f"Project path: {project_path}")

    # Rebuild venv if needed
    rebuild_venv_if_needed()

    # Load configuration
    config = load_config()
    node_id = config["node_id"]
    logger.info(f"Setting up for Node {node_id}")

    # Create systemd_reports directory
    systemd_reports_path = os.path.join(project_path, "systemd_reports")
    os.makedirs(systemd_reports_path, exist_ok=True)
    logger.info(f"Created systemd_reports directory: {systemd_reports_path}")

    # Create and Configure Systemd Service
    service_name = f"logger_lora_node_{node_id.lower()}"
    venv_python = os.path.join(project_path, ".venv", "bin", "python")
    service_content = f"""[Unit]
Description=Logger Lora Data Collection Service for Node {node_id}
After=network.target

[Service]
ExecStart={venv_python} {project_path}/main.py
WorkingDirectory={project_path}
User={os.getenv('SUDO_USER')}
Group={os.getenv('SUDO_USER')}
Restart=on-failure
RestartSec=60
StartLimitInterval={config['systemd']['restart_interval']}
StartLimitBurst={config['systemd']['max_restarts']}
Environment="PATH={os.path.dirname(venv_python)}:$PATH"

[Install]
WantedBy=multi-user.target
"""

    service_file = create_file(f"{service_name}.service", service_content)
    run_command(
        f"sudo cp {service_file} /etc/systemd/system/{service_file}",
        continue_on_error=True,
    )
    enable_and_start_systemd(service_file)

    # Create and Configure Systemd Timer
    timer_content = f"""[Unit]
Description=Run Logger Lora Data Collection every 30 minutes for Node {node_id}

[Timer]
OnBootSec=5min
OnUnitActiveSec=30min

[Install]
WantedBy=timers.target
"""

    timer_file = create_file(f"{service_name}.timer", timer_content)
    run_command(
        f"sudo cp {timer_file} /etc/systemd/system/{timer_file}",
        continue_on_error=True,
    )
    enable_and_start_systemd(timer_file)

    # Setup reboot counter
    setup_reboot_counter()

    # Setup systemd reboot service
    setup_systemd_reboot_service()

    # Setup LoRa pHAT
    setup_lora_phat()

    # Ensure correct permissions
    run_command(f"sudo chown -R {os.getenv('SUDO_USER')}:{os.getenv('SUDO_USER')} {project_path}")
    run_command(f"sudo chmod -R 755 {project_path}")
    run_command(f"sudo usermod -a -G dialout {os.getenv('SUDO_USER')}")

    logger.info("Setup process completed successfully")
    logger.info("Please reboot your Raspberry Pi for all changes to take effect.")
    logger.info("After reboot, you can test your LoRa pHAT with: 'rak811 -v -d version'")

if __name__ == "__main__":
    main()
