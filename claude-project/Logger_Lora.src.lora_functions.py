import json
from time import sleep
import os
from dotenv import load_dotenv
from .utils import get_sensor_hash, setup_logger
from datetime import datetime

load_dotenv()

logger = setup_logger("lora_functions", "lora_functions.log")

from rak811.rak811_v3 import Rak811


class LoRaManager:
    def __init__(self, config):
        self.lora = Rak811()
        self.config = config
        self.setup_lora()

    def setup_lora(self):
        try:
            self.lora.set_config("lora:work_mode:0")
            self.lora.set_config("lora:join_mode:1")
            self.lora.set_config(f'lora:region:{self.config["region"]}')
            self.lora.set_config(f'lora:dev_addr:{os.getenv("DEV_ADDR")}')
            self.lora.set_config(f'lora:apps_key:{os.getenv("APPS_KEY")}')
            self.lora.set_config(f'lora:nwks_key:{os.getenv("NWKS_KEY")}')
            self.lora.set_config(f'lora:dr:{self.config["data_rate"]}')

            self.lora.join()
            logger.info("Joined LoRaWAN network successfully")
        except Exception as e:
            logger.error(f"Error setting up LoRa: {e}")
            raise

    def send_data(self, data):
        try:
            json_payload = json.dumps(data)
            payload = json_payload.encode("utf-8")
            self.lora.send(payload)
            logger.info(f"Sent payload: {json_payload}")
        except Exception as e:
            logger.error(f"Error sending LoRa data: {e}")
            raise

    def close(self):
        try:
            self.lora.close()
            logger.info("LoRa connection closed successfully")
        except Exception as e:
            logger.error(f"Error closing LoRa connection: {e}")


def send_lora_data(data, config, sensor_metadata):
    logger.info("Initializing LoRa data transmission")
    lora_manager = LoRaManager(config)

    try:
        # Convert full sensor names to hashes
        hashed_data = {
            get_sensor_hash(k, sensor_metadata): v
            for k, v in data.items()
            if get_sensor_hash(k, sensor_metadata)
        }
        logger.debug(f"Hashed data: {hashed_data}")

        # Split data into chunks of 5 key-value pairs (leaving room for timestamp)
        chunks = [
            dict(list(hashed_data.items())[i : i + 5])
            for i in range(0, len(hashed_data), 5)
        ]
        logger.info(f"Data split into {len(chunks)} chunks")

        for i, chunk in enumerate(chunks):
            # Add timestamp to each chunk
            chunk["time"] = data["TIMESTAMP"].strftime("%Y%m%d%H%M%S")
            logger.debug(f"Sending chunk {i+1}: {chunk}")
            lora_manager.send_data(chunk)
            sleep(10)  # Wait 10 seconds between transmissions

        logger.info(f"Successfully sent {len(chunks)} LoRa packets")
    except Exception as e:
        logger.error(f"Error in send_lora_data: {e}")
    finally:
        lora_manager.close()


if __name__ == "__main__":
    # Test LoRaManager
    test_config = {"region": "US915", "data_rate": 3}
    lora_manager = LoRaManager(test_config)

    # Test send_data
    test_data = {"sensor1": 1.0, "sensor2": 2.0, "time": "20230703120000"}
    lora_manager.send_data(test_data)

    # Test send_lora_data
    test_sensor_metadata = [
        {"sensor_id": "sensor1", "hash": "001"},
        {"sensor_id": "sensor2", "hash": "002"},
    ]
    test_data_with_timestamp = {
        "TIMESTAMP": datetime.now(),
        "sensor1": 1.0,
        "sensor2": 2.0,
    }
    send_lora_data(test_data_with_timestamp, test_config, test_sensor_metadata)
