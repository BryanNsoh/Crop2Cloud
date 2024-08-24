from pycampbellcr1000 import CR1000
from datetime import datetime, timedelta
import os
import math
import json
import time
import subprocess
from .utils import setup_logger, increment_reboot_counter

logger = setup_logger("data_logger", "data_logger.log")

MAX_RETRIES = 5
MAX_DELAY = 180  # 3 minutes
MAX_REBOOTS = 5

def exponential_backoff(attempt):
    return min(MAX_DELAY, (2 ** attempt) * 5)  # 5, 10, 20, 40, 80, 160 seconds

def reboot_system():
    reboot_count = increment_reboot_counter()
    logger.warning(f"Initiating system reboot. Reboot count: {reboot_count}")
    
    if reboot_count > MAX_REBOOTS:
        logger.error(f"Maximum reboot count ({MAX_REBOOTS}) exceeded. Halting automatic reboots.")
        return

    try:
        with open('/tmp/logger_reboot_trigger', 'w') as f:
            f.write('reboot requested')
        logger.info("Reboot requested. System will reboot shortly.")
    except Exception as e:
        logger.error(f"Failed to request reboot: {e}")

def wait_for_usb_device(device_path, timeout=300, check_interval=1):
    start_time = time.time()
    while time.time() - start_time < timeout:
        if os.path.exists(device_path):
            logger.info(f"USB device {device_path} is available")
            return True
        time.sleep(check_interval)
    logger.error(f"Timeout waiting for USB device {device_path}")
    return False

def connect_to_datalogger(config):
    for attempt in range(MAX_RETRIES):
        try:
            logger.info(f"Attempting to connect to datalogger on port {config['port']} (Attempt {attempt + 1}/{MAX_RETRIES})")
            datalogger = CR1000.from_url(f"serial:{config['port']}:{config['baud_rate']}")
            logger.info(f"Successfully connected to datalogger on port {config['port']}")
            return datalogger
        except Exception as e:
            logger.error(f"Failed to connect to datalogger: {e}")
            if attempt < MAX_RETRIES - 1:
                delay = exponential_backoff(attempt)
                logger.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                logger.error("Max retries reached. Unable to connect to datalogger.")
                raise

def get_tables(datalogger):
    for attempt in range(MAX_RETRIES):
        try:
            table_names = datalogger.list_tables()
            logger.info(f"Retrieved {len(table_names)} table names: {table_names}")

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
            delay = exponential_backoff(attempt)
            logger.error(f"Error retrieving table names (Attempt {attempt + 1}/{MAX_RETRIES}): {e}")
            if attempt < MAX_RETRIES - 1:
                logger.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)
                # Attempt to re-establish connection
                try:
                    datalogger = CR1000.from_url(f"serial:{datalogger.url.split(':')[1]}:{datalogger.url.split(':')[2]}")
                except Exception as conn_err:
                    logger.error(f"Failed to re-establish connection: {conn_err}")
            else:
                logger.error("Max retries reached. Unable to retrieve table names.")
                return []

    return []

def get_data(datalogger, table_name, start, stop):
    try:
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
                elif key != "RecNbr" and key.endswith("_Avg"):
                    key = key[:-4]  # Remove "_Avg" suffix

                dict_entry[key] = value

                try:
                    if math.isnan(value):
                        dict_entry[key] = -9999
                except TypeError:
                    continue

            cleaned_data.append(dict_entry)

        cleaned_data.sort(key=lambda x: x["TIMESTAMP"])
        logger.info(f"Retrieved and cleaned {len(cleaned_data)} data points from {table_name_str}")
        
        if cleaned_data:
            logger.debug(f"Sample of cleaned data: {json.dumps(cleaned_data[:2], default=str)}")
        else:
            logger.warning("No data retrieved from datalogger")
        
        return cleaned_data
    except Exception as e:
        logger.error(f"Failed to get data from {table_name_str}: {e}")
        raise

def get_logger_time(datalogger):
    try:
        logger_time = datalogger.gettime()
        logger.info(f"Retrieved logger time: {logger_time}")
        return logger_time
    except Exception as e:
        logger.error(f"Failed to get logger time: {e}")
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
