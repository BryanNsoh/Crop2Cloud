from google.cloud import bigquery
from google.api_core.exceptions import NotFound
import subprocess
from datetime import datetime
import pandas as pd
from .utils import setup_logger

logger = setup_logger("cloud_functions", "cloud_functions.log")


def update_system_time():
    try:
        subprocess.run(["sudo", "timedatectl", "set-ntp", "true"])
        subprocess.run(["timedatectl"])
        logger.info("System time updated successfully")
    except Exception as e:
        logger.error(f"Failed to update system time: {e}")
        raise


def get_schema(list_dicts):
    if not list_dicts:
        logger.warning("Empty list provided for schema generation")
        return []

    def get_bq_type(value):
        if isinstance(value, (int, float)):
            return "FLOAT"
        elif isinstance(value, str):
            return "STRING"
        elif isinstance(value, bool):
            return "BOOLEAN"
        elif isinstance(value, bytes):
            return "BYTES"
        elif isinstance(value, (datetime, pd.Timestamp)):
            return "TIMESTAMP"
        else:
            logger.error(f"Unsupported data type: {type(value)}")
            raise ValueError(f"Unsupported data type: {type(value)}")

    sample_dict = list_dicts[0]
    schema = [
        bigquery.SchemaField(field_name, get_bq_type(sample_value))
        for field_name, sample_value in sample_dict.items()
    ]
    logger.info(f"Generated BigQuery schema with {len(schema)} fields")
    return schema


def update_bqtable(schema, table_id, table_data):
    client = bigquery.Client()

    job_config = bigquery.LoadJobConfig(
        schema=schema,
        autodetect=False,
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
    )

    logger.info(f"Attempting to load data into BigQuery table: {table_id}")
    job = client.load_table_from_json(table_data, table_id, job_config=job_config)

    try:
        job.result()  # Wait for the job to complete
        logger.info(f"Loaded {job.output_rows} rows into {table_id}")
    except Exception as e:
        logger.error(f"Error loading data into BigQuery: {e}")
        raise


def get_latest_entry_time(table_id):
    client = bigquery.Client()

    try:
        table = client.get_table(table_id)
        if "TIMESTAMP" not in [field.name for field in table.schema]:
            logger.warning(f"TIMESTAMP column not found in table {table_id}")
            return None

        query = f"SELECT MAX(TIMESTAMP) as latest FROM `{table_id}`"
        logger.debug(f"Executing query: {query}")
        query_job = client.query(query)
        results = query_job.result()

        for row in results:
            if row.latest is not None:
                logger.info(f"Retrieved latest entry time: {row.latest}")
                return row.latest

        logger.warning(f"No entries found in table {table_id}")
    except NotFound:
        logger.warning(
            f"Table '{table_id}' does not exist. A new table will be created."
        )
    except Exception as e:
        logger.error(f"Error retrieving latest entry time: {e}")
        raise

    return None


if __name__ == "__main__":
    # Test update_system_time
    update_system_time()

    # Test get_schema
    test_data = [
        {"field1": 1, "field2": "test", "field3": True, "field4": datetime.now()},
        {"field1": 2, "field2": "test2", "field3": False, "field4": datetime.now()},
    ]
    schema = get_schema(test_data)
    print("Generated schema:", schema)

    # Test update_bqtable (requires valid BigQuery credentials and table)
    # update_bqtable(schema, "your-project.your_dataset.your_table", test_data)

    # Test get_latest_entry_time (requires valid BigQuery credentials and table)
    # latest_time = get_latest_entry_time("your-project.your_dataset.your_table")
    # print("Latest entry time:", latest_time)
