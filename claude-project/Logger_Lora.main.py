import os
import logging
from datetime import datetime
from src import (
    connect_to_datalogger, get_tables, get_data, determine_time_range,
    update_system_time, get_schema, update_bqtable,
    setup_database, insert_data_to_db, get_latest_timestamp,
    send_lora_data, load_config, load_sensor_metadata
)
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Load configuration
config = load_config('config.yaml')

# Configure logging
logging.basicConfig(
    filename=os.path.join('logs', 'application.log'),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] - %(message)s",
)

logger = logging.getLogger(__name__)

def main():
    try:
        # Update system time
        update_system_time()

        # Load sensor metadata
        sensor_metadata = load_sensor_metadata(config['sensor_metadata'])

        # Connect to datalogger
        datalogger = connect_to_datalogger(config['datalogger'])

        # Get table names
        table_names = get_tables(datalogger)
        if not table_names:
            logger.error("No tables found in datalogger")
            return

        # Get latest timestamp from local database
        latest_time = get_latest_timestamp(config['database']['name'])

        # Determine start and stop times
        start, stop = determine_time_range(latest_time)

        # Get table data
        table_data = get_data(datalogger, table_names[0], start, stop)
        if not table_data:
            logger.info("No new data to process")
            return

        # Update BigQuery table
        schema = get_schema(table_data)
        update_bqtable(schema, config['cloud']['table_id'], table_data)

        # Update local SQLite database
        setup_database(schema, config['database']['name'])
        insert_data_to_db(table_data, config['database']['name'])

        # Send data via LoRa
        send_lora_data(table_data, config['lora'], sensor_metadata)

        logger.info("Data processing and upload successful!")

    except Exception as e:
        logger.error(f"An error occurred in the main process: {e}", exc_info=True)
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()