import os
import subprocess
import shutil
from pathlib import Path
import json
from src.utils import setup_logger

# Set up logging
logger = setup_logger("setup", "setup.log")

# Load configuration from config.json
with open("./config.json", "r") as config_file:
    config = json.load(config_file)


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


def main():
    logger.info("Starting setup process")

    check_permissions()

    # Set your project path
    project_path = os.getcwd()
    logger.info(f"Project path: {project_path}")

    # Create systemd_reports directory
    systemd_reports_path = os.path.join(project_path, "systemd_reports")
    os.makedirs(systemd_reports_path, exist_ok=True)
    logger.info(f"Created systemd_reports directory: {systemd_reports_path}")

    # Install and Upgrade Python Modules
    commands = config["commands"]

    for cmd in commands:
        stdout, stderr = run_command(cmd, continue_on_error=True)
        logger.debug(f"Command output: {stdout}")
        if stderr:
            logger.warning(f"Command error output: {stderr}")

    sudo_path = shutil.which("sudo")
    logger.info(f"Sudo path: {sudo_path}")

    # Create and Configure Systemd Services and Timers
    units = config["units"]

    # Create, enable, and start the systemd units
    for unit in units:
        logger.info(f"Creating systemd unit: {unit['name']}.service")
        service_content = unit["service"].format(
            project_path=project_path, systemd_reports_path=systemd_reports_path
        )
        service_file = create_file(f"{unit['name']}.service", service_content)
        run_command(
            f"sudo cp {service_file} /etc/systemd/system/{service_file}",
            continue_on_error=True,
        )
        enable_and_start_systemd(service_file)

        if "timer" in unit:
            logger.info(f"Creating systemd timer: {unit['name']}.timer")
            timer_file = create_file(f"{unit['name']}.timer", unit["timer"])
            run_command(
                f"sudo cp {timer_file} /etc/systemd/system/{timer_file}",
                continue_on_error=True,
            )
            enable_and_start_systemd(timer_file)

    logger.info("Setup process completed successfully")


if __name__ == "__main__":
    main()
