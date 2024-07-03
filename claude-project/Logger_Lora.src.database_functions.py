import sqlite3
from datetime import datetime
from .utils import setup_logger

logger = setup_logger("database_functions", "database_functions.log")


def setup_database(columns, db_name):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    columns_str = ", ".join([f"{col} TEXT" for col in columns])
    create_table_stmt = f"CREATE TABLE IF NOT EXISTS data_table ({columns_str})"

    try:
        cursor.execute(create_table_stmt)
        conn.commit()
        logger.info(f"Database {db_name} set up successfully")
    except Exception as e:
        logger.error(f"Error setting up database {db_name}: {e}")
        raise
    finally:
        conn.close()


def insert_data_to_db(data, db_name):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    columns = ", ".join(data[0].keys())
    placeholders = ", ".join(["?" for _ in data[0]])
    insert_stmt = f"INSERT INTO data_table ({columns}) VALUES ({placeholders})"

    try:
        cursor.executemany(insert_stmt, [tuple(row.values()) for row in data])
        conn.commit()
        logger.info(f"Inserted {len(data)} rows into {db_name}")
    except Exception as e:
        logger.error(f"Error inserting data into {db_name}: {e}")
        raise
    finally:
        conn.close()


def get_latest_timestamp(db_name):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT TIMESTAMP FROM data_table ORDER BY TIMESTAMP DESC LIMIT 1"
        )
        result = cursor.fetchone()
        if result:
            logger.info(f"Retrieved latest timestamp: {result[0]}")
            return result[0]
        else:
            logger.info("No data found in the database")
            return None
    except sqlite3.OperationalError as e:
        logger.warning(f"Table might not exist in {db_name}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error retrieving latest timestamp from {db_name}: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    # Test setup_database
    from google.cloud import bigquery

    test_schema = [
        bigquery.SchemaField("TIMESTAMP", "TIMESTAMP"),
        bigquery.SchemaField("sensor1", "FLOAT"),
        bigquery.SchemaField("sensor2", "FLOAT"),
    ]
    setup_database(test_schema, "test_database.db")

    # Test insert_data_to_db
    test_data = [
        {"TIMESTAMP": datetime.now(), "sensor1": 1.0, "sensor2": 2.0},
        {"TIMESTAMP": datetime.now(), "sensor1": 3.0, "sensor2": 4.0},
    ]
    insert_data_to_db(test_data, "test_database.db")

    # Test get_latest_timestamp
    latest_timestamp = get_latest_timestamp("test_database.db")
    print(f"Latest timestamp: {latest_timestamp}")
