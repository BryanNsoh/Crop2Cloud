import sys
import os
import time
from datetime import datetime, timedelta
import traceback
import json
import random
from src.utils import (
    load_config,
    setup_logger,
    get_project_root,
    reset_reboot_counter,
    increment_reboot_counter,
    read_reboot_counter
)
from src import (
    connect_to_datalogger,
    get_tables,
    get_data,
    get_logger_time,
    setup_database,
    insert_data_to_db,
    send_lora_data,
    load_sensor_metadata,
    reboot_system,
    wait_for_usb_device
)

logger = setup_logger("main", "main.log")

MAX_FAILURES = 3
RETRY_DELAY = 60  # 1 minute delay between retries

def main():
    logger.info("=== System started ===")
    failure_count = 0
    config = load_config()

    while True:
        try:
            logger.info(f"Starting main process (Attempt {failure_count + 1}/{MAX_FAILURES})")
            
            logger.info(f"Running on Node {config['node_id']}")
            
            project_root = get_project_root()
            logger.debug(f"Project root: {project_root}")
            logger.debug(f"Sensor metadata path: {os.path.join(project_root, config['sensor_metadata'])}")
            
            db_dir = os.path.dirname(config['database']['name'])
            if not os.path.exists(db_dir):
                logger.info(f"Database directory does not exist. Attempting to create: {db_dir}")
                os.makedirs(db_dir, exist_ok=True)
            
            if not os.access(db_dir, os.W_OK):
                logger.error(f"No write permission for database directory: {db_dir}")
                return

            sensor_metadata = load_sensor_metadata(config["sensor_metadata"])
            logger.info(f"Loaded metadata for {len(sensor_metadata)} sensors")

            # Wait for USB device
            if not wait_for_usb_device(config["datalogger"]["port"]):
                raise Exception("USB device not available")

            datalogger = connect_to_datalogger(config["datalogger"])

            table_names = get_tables(datalogger)
            if not table_names:
                raise Exception("Failed to retrieve table names")

            logger_time = get_logger_time(datalogger)
            start_time = logger_time - timedelta(minutes=35)  # Get data from last 35 minutes
            
            table_data = get_data(datalogger, table_names[0], start_time, logger_time)
            if not table_data:
                logger.info("No new data to process")
                continue

            logger.info(f"Retrieved {len(table_data)} data points")
            logger.debug(f"Sample of retrieved data: {json.dumps(table_data[:2], default=str)}")

            latest_data = table_data[-1]  # Get the last (most recent) data point
            logger.info(f"Latest timestamp from logger: {latest_data['TIMESTAMP']}")
            logger.debug(f"Latest data point: {json.dumps(latest_data, default=str)}")

            setup_database(latest_data.keys(), config["database"]["name"])
            insert_data_to_db([latest_data], config["database"]["name"])

            send_lora_data(latest_data, config, sensor_metadata, clip_floats=config.get("clip_floats", False))

            logger.info("Data processing and transmission successful!")
            
            # Reset the failure counter after a successful run
            failure_count = 0
            reset_reboot_counter()
            logger.info("Reboot counter reset after successful execution")

            # Wait for the next scheduled execution only if successful
            interval = config['schedule']['interval_minutes']
            logger.info(f"Execution successful. Waiting for {interval} minutes before next scheduled execution")
            time.sleep(interval * 60)

        except Exception as e:
            logger.error(f"An error occurred in the main process: {str(e)}")
            logger.error(traceback.format_exc())
            failure_count += 1
            if failure_count >= MAX_FAILURES:
                logger.error(f"Max failures ({MAX_FAILURES}) reached. Initiating system reboot.")
                reboot_system()
                logger.info("=== System reboot initiated ===")
                return  # Exit the script, it will be restarted by the system
            else:
                logger.warning(f"Failure count: {failure_count}/{MAX_FAILURES}")
                logger.info(f"Retrying in {RETRY_DELAY} seconds...")
                time.sleep(RETRY_DELAY)

if __name__ == "__main__":
    main()
