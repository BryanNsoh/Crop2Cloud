import sys
from src.utils import load_config, setup_logger
from src import (
    connect_to_datalogger,
    get_tables,
    get_data,
    update_system_time,
    setup_database,
    insert_data_to_db,
    send_lora_data,
    load_sensor_metadata,
    get_project_root,
)
import os
from datetime import datetime, timedelta
import traceback

logger = setup_logger("main", "main.log")

def main():
    try:
        logger.info("Starting main process")
        
        # Load configuration
        logger.debug("Loading configuration")
        config = load_config()
        logger.info(f"Running on Node {config['node_id']}")
        
        project_root = get_project_root()
        logger.debug(f"Project root: {project_root}")
        logger.debug(f"Sensor metadata path: {os.path.join(project_root, config['sensor_metadata'])}")
        
        
        # Check if the database directory exists and is writable
        db_dir = os.path.dirname(config['database']['name'])
        if not os.path.exists(db_dir):
            logger.info(f"Database directory does not exist. Attempting to create: {db_dir}")
            os.makedirs(db_dir, exist_ok=True)
        
        if not os.access(db_dir, os.W_OK):
            logger.error(f"No write permission for database directory: {db_dir}")
            return

        # Update system time
        logger.debug("Updating system time")
        update_system_time()

        # Load sensor metadata
        logger.debug("Loading sensor metadata")
        sensor_metadata = load_sensor_metadata(config["sensor_metadata"])
        logger.info(f"Loaded metadata for {len(sensor_metadata)} sensors")

        # Connect to datalogger
        logger.debug("Connecting to datalogger")
        datalogger = connect_to_datalogger(config["datalogger"])

        # Get table names
        logger.debug("Getting table names from datalogger")
        table_names = get_tables(datalogger)
        if not table_names:
            logger.error("No suitable tables found in datalogger")
            return

        # Get data for the last hour
        stop = datetime.now()
        start = stop - timedelta(hours=1)
        logger.info(f"Retrieving data from logger for time range: start={start}, stop={stop}")

        # Get table data
        logger.debug("Getting data from datalogger")
        table_data = get_data(datalogger, table_names[0], start, stop)
        if not table_data:
            logger.info("No new data to process")
            return

        logger.info(f"Retrieved {len(table_data)} data points")

        # Get the latest data point
        latest_data = table_data[-1]
        logger.info(f"Latest timestamp from logger: {latest_data['TIMESTAMP']}")

        # Setup and update local SQLite database
        logger.debug("Setting up database")
        setup_database(latest_data.keys(), config["database"]["name"])
        logger.debug("Inserting data into database")
        insert_data_to_db([latest_data], config["database"]["name"])

        # Send data via LoRa
        logger.debug("Sending data via LoRa")
        send_lora_data(latest_data, config["lora"], sensor_metadata)

        logger.info("Data processing and transmission successful!")

    except Exception as e:
        logger.error(f"An error occurred in the main process: {str(e)}")
        logger.error(traceback.format_exc())
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()
