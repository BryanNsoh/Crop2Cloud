from pycampbellcr1000 import CR1000
import logging
from datetime import datetime, timedelta
import math

logger = logging.getLogger(__name__)

def connect_to_datalogger(config):
    try:
        datalogger = CR1000.from_url(f"serial:{config['port']}:{config['baud_rate']}")
        logger.info("Successfully connected to datalogger")
        return datalogger
    except Exception as e:
        logger.error(f"Failed to connect to datalogger: {e}")
        raise

def get_tables(datalogger):
    try:
        table_names = datalogger.list_tables()
        logger.info(f"Retrieved table names: {table_names}")
        return table_names
    except Exception as e:
        logger.error(f"Failed to get table names: {e}")
        raise

def get_data(datalogger, table_name, start, stop):
    try:
        table_data = datalogger.get_data(table_name, start, stop)
        cleaned_data = []

        for label in table_data:
            dict_entry = {}
            for key, value in label.items():
                key = key.replace("b'", "").replace("'", "")

                if key == "Datetime":
                    key = "TIMESTAMP"

                dict_entry[key] = value

                try:
                    if math.isnan(value):
                        dict_entry[key] = -9999
                except TypeError:
                    continue

            cleaned_data.append(dict_entry)

        cleaned_data.sort(key=lambda x: x["TIMESTAMP"])
        logger.info(f"Retrieved and cleaned data from {table_name}")
        return cleaned_data
    except Exception as e:
        logger.error(f"Failed to get data from {table_name}: {e}")
        raise

def determine_time_range(latest_time):
    if latest_time:
        start = datetime.fromisoformat(latest_time) + timedelta(seconds=1)
    else:
        start = datetime.now() - timedelta(days=2)
    
    stop = datetime.now()
    logger.info(f"Determined time range: start={start}, stop={stop}")
    return start, stop