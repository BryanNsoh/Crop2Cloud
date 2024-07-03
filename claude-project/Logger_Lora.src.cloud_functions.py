from google.cloud import bigquery
from google.api_core.exceptions import NotFound
import logging
import subprocess
from datetime import datetime

logger = logging.getLogger(__name__)

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
            raise ValueError(f"Unsupported data type: {type(value)}")

    sample_dict = list_dicts[0]
    schema = [
        bigquery.SchemaField(field_name, get_bq_type(sample_value))
        for field_name, sample_value in sample_dict.items()
    ]
    logger.info("Generated BigQuery schema")
    return schema

def update_bqtable(schema, table_id, table_data):
    client = bigquery.Client()
    
    job_config = bigquery.LoadJobConfig(
        schema=schema,
        autodetect=False,
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
    )

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
            return None

        query = f"SELECT MAX(TIMESTAMP) as latest FROM `{table_id}`"
        query_job = client.query(query)
        results = query_job.result()

        for row in results:
            if row.latest is not None:
                logger.info(f"Retrieved latest entry time: {row.latest}")
                return row.latest
    except NotFound:
        logger.warning(f"Table '{table_id}' does not exist. A new table will be created.")
    except Exception as e:
        logger.error(f"Error retrieving latest entry time: {e}")
        raise

    return None