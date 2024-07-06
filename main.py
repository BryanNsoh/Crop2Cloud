import sys
import os
import time
from datetime import datetime, timedelta
import traceback
import json
import random
from src.utils import load_config, setup_logger, get_project_root
from src import (
    connect_to_datalogger,
    get_tables,
    get_data,
    update_system_time,
    setup_database,
    insert_data_to_db,
    send_lora_data,
    load_sensor_metadata,
)

logger = setup_logger("main", "main.log")

def main():
    while True:
        try:
            # Add a random delay between 1 and 5 seconds
            time.sleep(random.uniform(1, 5))

            logger.info("Starting main process")
            
            config = load_config()
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

            update_system_time()

            sensor_metadata = load_sensor_metadata(config["sensor_metadata"])
            logger.info(f"Loaded metadata for {len(sensor_metadata)} sensors")

            datalogger = connect_to_datalogger(config["datalogger"])

            table_names = get_tables(datalogger)
            if not table_names:
                logger.error("No suitable tables found in datalogger")
                return

            stop = datetime.now()
            start = stop - timedelta(hours=1)
            logger.info(f"Retrieving data from logger for time range: start={start}, stop={stop}")

            table_data = get_data(datalogger, table_names[0], start, stop)
            if not table_data:
                logger.info("No new data to process")
                return

            logger.info(f"Retrieved {len(table_data)} data points")
            logger.debug(f"Sample of retrieved data: {json.dumps(table_data[:2], default=str)}")

            latest_data = table_data[-1]
            logger.info(f"Latest timestamp from logger: {latest_data['TIMESTAMP']}")
            logger.debug(f"Latest data point: {json.dumps(latest_data, default=str)}")

            setup_database(latest_data.keys(), config["database"]["name"])
            insert_data_to_db([latest_data], config["database"]["name"])

            send_lora_data(latest_data, config, sensor_metadata, clip_floats=config.get("clip_floats", False))

            logger.info("Data processing and transmission successful!")

        except Exception as e:
            logger.error(f"An error occurred in the main process: {str(e)}")
            logger.error(traceback.format_exc())
        finally:
            # Wait for the next scheduled execution
            interval = config['schedule']['interval_minutes']
            logger.info(f"Waiting for {interval} minutes before next execution")
            time.sleep(interval * 60)

if __name__ == "__main__":
    main()
