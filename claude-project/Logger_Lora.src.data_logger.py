from pycampbellcr1000 import CR1000
from datetime import datetime, timedelta
import math
from .utils import setup_logger

logger = setup_logger("data_logger", "data_logger.log")

def connect_to_datalogger(config):
    try:
        datalogger = CR1000.from_url(f"serial:{config['port']}:{config['baud_rate']}")
        logger.info(f"Successfully connected to datalogger on port {config['port']}")
        return datalogger
    except Exception as e:
        logger.error(f"Failed to connect to datalogger: {e}")
        raise

def get_tables(datalogger):
    try:
        table_names = datalogger.list_tables()
        logger.info(f"Retrieved {len(table_names)} table names: {table_names}")

        # Find the table that is not Status, DataTableInfo, or Public
        desired_table = next(
            (
                table
                for table in table_names
                if table not in [b"Status", b"DataTableInfo", b"Public"]
            ),
            None,
        )

        if desired_table:
            logger.info(f"Selected table for data retrieval: {desired_table}")
            return [desired_table]
        else:
            logger.error("No suitable table found for data retrieval")
            return []
    except Exception as e:
        logger.error(f"Failed to get table names: {e}")
        raise

def get_data(datalogger, table_name, start, stop):
    try:
        # Decode table_name from bytes to string
        table_name_str = table_name.decode("utf-8")
        logger.info(
            f"Attempting to retrieve data from {table_name_str} between {start} and {stop}"
        )
        table_data = datalogger.get_data(table_name_str, start, stop)
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
        logger.info(f"Retrieved and cleaned data from {table_name_str}")
        return cleaned_data
    except Exception as e:
        logger.error(f"Failed to get data from {table_name_str}: {e}")
        raise

def determine_time_range(latest_time):
    if latest_time:
        start = datetime.fromisoformat(latest_time) + timedelta(seconds=1)
        logger.info(f"Using latest time from database: {start}")
    else:
        start = datetime.now() - timedelta(days=2)
        logger.info(f"No latest time found, using default start time: {start}")

    stop = datetime.now()
    logger.info(f"Determined time range: start={start}, stop={stop}")
    return start, stop
