import yaml
import logging
import os
import sys

class RepoLogger:
    def __init__(self, log_dir="src/logs"):
        """
        Initializes the logger.

        Args:
            log_dir (str, optional): The directory to store log files. Defaults to 'src/logs'.
        """
        self.log_dir = log_dir

    def setup_logger(self, level=logging.INFO):
        """Sets up the logger with a file handler and formatter."""
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

        # Get the name of the calling script for the log file name
        log_name = os.path.splitext(os.path.basename(sys.argv[0]))[0]
        log_file = os.path.join(self.log_dir, f"{log_name}.log")

        logging.basicConfig(
            filename=log_file,
            level=level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            filemode="w",
        )

    def get_logger(self, level=logging.INFO):
        """
        Retrieves a logger, using the calling script's name for the log file.

        Args:
            level (int, optional): The logging level to be set. Defaults to logging.INFO.

        Returns:
            logging.Logger: The logger instance.
        """
        self.setup_logger(level)
        return logging.getLogger(__name__)

def get_logger(log_dir="src/logs", level=logging.INFO):
    """
    Helper function to get a logger instance.

    Args:
        log_dir (str, optional): The directory to store log files. Defaults to 'src/logs'.
        level (int, optional): The logging level to be set. Defaults to logging.INFO.

    Returns:
        logging.Logger: The logger instance.
    """
    repo_logger = RepoLogger(log_dir)
    return repo_logger.get_logger(level)

def load_config(config_file):
    logger = get_logger()
    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        logger.info(f"Configuration loaded from {config_file}")
        return config
    except Exception as e:
        logger.error(f"Error loading configuration from {config_file}: {e}")
        raise

def load_sensor_metadata(sensor_file):
    logger = get_logger()
    try:
        with open(sensor_file, 'r') as f:
            sensor_metadata = yaml.safe_load(f)
        logger.info(f"Sensor metadata loaded from {sensor_file}")
        return sensor_metadata
    except Exception as e:
        logger.error(f"Error loading sensor metadata from {sensor_file}: {e}")
        raise

def get_sensor_hash(sensor_id, sensor_metadata):
    logger = get_logger()
    for sensor in sensor_metadata:
        if sensor['sensor_id'] == sensor_id:
            return sensor['hash']
    logger.warning(f"No hash found for sensor_id: {sensor_id}")
    return None