import yaml
import logging
from logging.handlers import RotatingFileHandler
import os
import sys


class CustomFormatter(logging.Formatter):
    """Custom formatter with color coding for different log levels"""

    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    FORMATS = {
        logging.DEBUG: grey + format + reset,
        logging.INFO: grey + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset,
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


def get_project_root():
    """Get the project root directory."""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def setup_logger(name, log_file, level=logging.INFO):
    """Function to setup as many loggers as you want"""
    project_root = get_project_root()
    log_dir = os.path.join(project_root, "logs")
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    full_path = os.path.join(log_dir, log_file)

    handler = RotatingFileHandler(full_path, maxBytes=5 * 1024 * 1024, backupCount=5)
    handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(CustomFormatter())
    logger.addHandler(console_handler)

    return logger


def load_config(config_file):
    logger = setup_logger("utils", "utils.log")
    project_root = get_project_root()
    full_config_path = os.path.join(project_root, config_file)
    try:
        with open(full_config_path, "r") as f:
            config = yaml.safe_load(f)
        logger.info(f"Configuration loaded from {full_config_path}")
        return config
    except Exception as e:
        logger.error(f"Error loading configuration from {full_config_path}: {e}")
        raise


def load_sensor_metadata(sensor_file):
    logger = setup_logger("utils", "utils.log")
    project_root = get_project_root()
    full_sensor_path = os.path.join(project_root, sensor_file)
    try:
        with open(full_sensor_path, "r") as f:
            sensor_metadata = yaml.safe_load(f)
        logger.info(f"Sensor metadata loaded from {full_sensor_path}")
        return sensor_metadata
    except Exception as e:
        logger.error(f"Error loading sensor metadata from {full_sensor_path}: {e}")
        raise


def get_sensor_hash(sensor_id, sensor_metadata):
    logger = setup_logger("utils", "utils.log")
    for sensor in sensor_metadata:
        if sensor["sensor_id"] == sensor_id:
            logger.debug(f"Hash found for sensor_id: {sensor_id}")
            return sensor["hash"]
    logger.warning(f"No hash found for sensor_id: {sensor_id}")
    return None


if __name__ == "__main__":
    # Test the logger
    logger = setup_logger("test_logger", "test.log")
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.critical("This is a critical message")

    # Test config loading
    try:
        config = load_config("config/config.yaml")
        print("Loaded config:", config)
    except Exception as e:
        print(f"Error loading config: {e}")

    # Test sensor metadata loading
    try:
        sensor_metadata = load_sensor_metadata("config/sensor_mapping.yaml")
        print("Loaded sensor metadata:", sensor_metadata)
    except Exception as e:
        print(f"Error loading sensor metadata: {e}")

    # Test get_sensor_hash
    if "sensor_metadata" in locals():
        test_sensor_id = "IRT5023A1xx24"
        sensor_hash = get_sensor_hash(test_sensor_id, sensor_metadata)
        print(f"Hash for sensor {test_sensor_id}: {sensor_hash}")
