import sqlite3
from datetime import datetime
from .utils import setup_logger
import os
import json

logger = setup_logger("database_functions", "database_functions.log")

def setup_database(columns, db_name):
    try:
        os.makedirs(os.path.dirname(db_name), exist_ok=True)
        logger.info(f"Ensuring directory exists for database: {db_name}")
        
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()

        columns_str = ", ".join([f"{col} TEXT" for col in columns])
        create_table_stmt = f"CREATE TABLE IF NOT EXISTS data_table ({columns_str})"

        cursor.execute(create_table_stmt)
        conn.commit()
        logger.info(f"Database {db_name} set up successfully")
        logger.debug(f"Created table with columns: {columns_str}")
    except sqlite3.OperationalError as e:
        logger.error(f"SQLite operational error setting up database {db_name}: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error setting up database {db_name}: {e}")
        raise
    finally:
        if 'conn' in locals():
            conn.close()

def insert_data_to_db(data, db_name):
    try:
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()

        columns = ", ".join(data[0].keys())
        placeholders = ", ".join(["?" for _ in data[0]])
        insert_stmt = f"INSERT INTO data_table ({columns}) VALUES ({placeholders})"

        cursor.executemany(insert_stmt, [tuple(row.values()) for row in data])
        conn.commit()
        logger.info(f"Inserted {len(data)} rows into {db_name}")
        logger.debug(f"Sample of inserted data: {json.dumps(data[:2], default=str)}")
    except sqlite3.OperationalError as e:
        logger.error(f"SQLite operational error inserting data into {db_name}: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error inserting data into {db_name}: {e}")
        raise
    finally:
        if 'conn' in locals():
            conn.close()
