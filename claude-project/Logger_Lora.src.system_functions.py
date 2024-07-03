import subprocess
from .utils import setup_logger

logger = setup_logger("system_functions", "system_functions.log")


def update_system_time():
    try:
        subprocess.run(["sudo", "timedatectl", "set-ntp", "true"])
        subprocess.run(["timedatectl"])
        logger.info("System time updated successfully")
    except Exception as e:
        logger.error(f"Failed to update system time: {e}")
        raise


if __name__ == "__main__":
    update_system_time()
