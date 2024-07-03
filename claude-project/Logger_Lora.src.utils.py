import yaml
import logging

logger = logging.getLogger(__name__)

def load_config(config_file):
    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        logger.info(f"Configuration loaded from {config_file}")
        return config
    except Exception as e:
        logger.error(f"Error loading configuration from {config_file}: {e}")
        raise

def load_sensor_metadata(sensor_file):
    try:
        with open(sensor_file, 'r') as f:
            sensor_metadata = yaml.safe_load(f)
        logger.info(f"Sensor metadata loaded from {sensor_file}")
        return sensor_metadata
    except Exception as e:
        logger.error(f"Error loading sensor metadata from {sensor_file}: {e}")
        raise

def get_sensor_hash(sensor_id, sensor_metadata):
    for sensor in sensor_metadata:
        if sensor['sensor_id'] == sensor_id:
            return sensor['hash']
    logger.warning(f"No hash found for sensor_id: {sensor_id}")
    return None