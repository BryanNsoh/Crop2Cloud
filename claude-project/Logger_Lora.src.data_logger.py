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
        return table_names
    except Exception as e:
        logger.error(f"Failed to get table names: {e}")
        raise


def get_data(datalogger, table_name, start, stop):
    try:
        logger.info(
            f"Attempting to retrieve data from {table_name} between {start} and {stop}"
        )
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
                        logger.warning(
                            f"NaN value found for {key}, replaced with -9999"
                        )
                except TypeError:
                    logger.debug(f"Non-numeric value for {key}: {value}")
                    continue

            cleaned_data.append(dict_entry)

        cleaned_data.sort(key=lambda x: x["TIMESTAMP"])
        logger.info(
            f"Retrieved and cleaned {len(cleaned_data)} data points from {table_name}"
        )
        return cleaned_data
    except Exception as e:
        logger.error(f"Failed to get data from {table_name}: {e}")
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


if __name__ == "__main__":
    # Test connect_to_datalogger
    test_config = {"port": "/dev/ttyUSB0", "baud_rate": 38400}
    try:
        datalogger = connect_to_datalogger(test_config)
        print("Successfully connected to datalogger")
    except Exception as e:
        print(f"Failed to connect to datalogger: {e}")

    # Test get_tables
    if "datalogger" in locals():
        try:
            tables = get_tables(datalogger)
            print(f"Retrieved tables: {tables}")
        except Exception as e:
            print(f"Failed to get tables: {e}")

    # Test get_data
    if "datalogger" in locals() and "tables" in locals() and tables:
        start = datetime.now() - timedelta(hours=1)
        stop = datetime.now()
        try:
            data = get_data(datalogger, tables[0], start, stop)
            print(f"Retrieved {len(data)} data points")
            if data:
                print("Sample data point:", data[0])
        except Exception as e:
            print(f"Failed to get data: {e}")

    # Test determine_time_range
    latest_time = "2023-07-03T12:00:00"
    start, stop = determine_time_range(latest_time)
    print(f"Determined time range: start={start}, stop={stop}")

    # Test determine_time_range with no latest time
    start, stop = determine_time_range(None)
    print(f"Determined time range (no latest time): start={start}, stop={stop}")
