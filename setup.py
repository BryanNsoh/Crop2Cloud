import os
import subprocess
import shutil
from pathlib import Path
import yaml
import sys
from src.utils import setup_logger, load_config

# Set up logging
logger = setup_logger("setup", "setup.log")

def check_permissions():
    if os.geteuid() != 0:
        logger.error(
            "This script requires root privileges to manage systemd services and timers. Please run with sudo."
        )
        exit(1)

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

def rebuild_venv_if_needed():
    venv_path = os.path.join(os.getcwd(), ".venv")
    if not os.path.exists(venv_path) or sys.prefix != venv_path:
        logger.info("Rebuilding virtual environment")
        run_command(f"python3 -m venv {venv_path}")
        run_command(f"{venv_path}/bin/pip install -r requirements.txt")

def main():
    logger.info("Starting setup process")

    check_permissions()

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

    sudo_path = shutil.which("sudo")
    logger.info(f"Sudo path: {sudo_path}")

    # Create and Configure Systemd Service
    service_name = f"logger_lora_node_{node_id.lower()}"
    venv_python = os.path.join(project_path, ".venv", "bin", "python")
    service_content = f"""[Unit]
Description=Logger Lora Data Collection Service for Node {node_id}
After=network.target

[Service]
ExecStart={venv_python} {project_path}/main.py
WorkingDirectory={project_path}
User={os.getenv('USER')}
Group={os.getenv('USER')}
Restart=always
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

    # Set correct permissions
    run_command(f"sudo chown -R {os.getenv('USER')}:{os.getenv('USER')} {project_path}")
    run_command(f"sudo chmod -R 755 {project_path}")

    logger.info("Setup process completed successfully")

if __name__ == "__main__":
    main()