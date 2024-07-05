import yaml
import logging
from logging.handlers import RotatingFileHandler
import os
import sys

class CustomFormatter(logging.Formatter):
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

def setup_logger(name, log_file, level=logging.DEBUG):
    project_root = get_project_root()
    log_dir = os.path.join(project_root, "logs")
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    full_path = os.path.join(log_dir, log_file)

    # Create a logger
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Create handlers
    file_handler = RotatingFileHandler(full_path, maxBytes=5*1024*1024, backupCount=5)
    console_handler = logging.StreamHandler(sys.stdout)

    # Create formatters
    file_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    console_formatter = CustomFormatter()

    # Set formatters
    file_handler.setFormatter(file_formatter)
    console_handler.setFormatter(console_formatter)

    # Add handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

def load_config():
    logger = setup_logger("utils", "utils.log")
    try:
        with open("config/config.yaml", "r") as f:
            config = yaml.safe_load(f)

        node_id = config["node_id"]

        # Merge node-specific config with general config
        node_config = config["node_configs"][node_id]
        config["lora"].update(node_config["lora"])

        # Format database name with node_id
        config["database"]["name"] = config["database"]["name"].format(node_id=node_id)

        # Ensure data directory exists
        data_dir = os.path.dirname(config["database"]["name"])
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)

        logger.info(f"Loaded configuration for Node {node_id}")
        logger.info(f"Database will be stored at: {config['database']['name']}")
        return config
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        raise

def get_project_root():
    return os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

def load_sensor_metadata(sensor_file):
    logger = setup_logger("utils", "utils.log")
    project_root = get_project_root()
    full_sensor_path = os.path.join(project_root, sensor_file)
    logger.debug(f"Attempting to load sensor metadata from: {full_sensor_path}")
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
