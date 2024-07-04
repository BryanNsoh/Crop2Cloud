from src.utils import load_config, setup_logger
from src import (
    connect_to_datalogger,
    get_tables,
    get_data,
    determine_time_range,
    update_system_time,
    setup_database,
    insert_data_to_db,
    get_latest_timestamp,
    send_lora_data,
    load_sensor_metadata,
)

logger = setup_logger("main", "main.log")

def main():
    try:
        # Load configuration
        config = load_config()
        logger.info(f"Running on Node {config['node_id']}")

        # Update system time
        update_system_time()

        # Load sensor metadata
        sensor_metadata = load_sensor_metadata(config["sensor_metadata"])
        logger.info(f"Loaded metadata for {len(sensor_metadata)} sensors")

        # Connect to datalogger
        datalogger = connect_to_datalogger(config["datalogger"])

        # Get table names
        table_names = get_tables(datalogger)
        if not table_names:
            logger.error("No suitable tables found in datalogger")
            return

        # Get latest timestamp from local database
        latest_time = get_latest_timestamp(config["database"]["name"])

        # Determine start and stop times
        start, stop = determine_time_range(latest_time)

        # Get table data
        table_data = get_data(datalogger, table_names[0], start, stop)
        if not table_data:
            logger.info("No new data to process")
            return

        # Update local SQLite database
        setup_database(table_data[0].keys(), config["database"]["name"])
        insert_data_to_db(table_data, config["database"]["name"])

        # Send data via LoRa
        for data_point in table_data:
            send_lora_data(data_point, config["lora"], sensor_metadata)

        logger.info("Data processing and transmission successful!")

    except Exception as e:
        logger.error(f"An error occurred in the main process: {e}", exc_info=True)
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()