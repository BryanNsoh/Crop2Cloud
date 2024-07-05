import json
from time import sleep
from .utils import get_sensor_hash, setup_logger
from datetime import datetime
from rak811.rak811_v3 import Rak811

logger = setup_logger("lora_functions", "lora_functions.log")

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
            self.lora.set_config(f'lora:dev_addr:{self.config["dev_addr"]}')
            self.lora.set_config(f'lora:apps_key:{self.config["apps_key"]}')
            self.lora.set_config(f'lora:nwks_key:{self.config["nwks_key"]}')
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
            if get_sensor_hash(k, sensor_metadata) and k != "TIMESTAMP"
        }
        logger.debug(f"Hashed data: {hashed_data}")

        # Add timestamp to the data
        hashed_data["time"] = data["TIMESTAMP"].strftime("%Y%m%d%H%M%S")

        # Split data into chunks of 6 key-value pairs (including timestamp)
        chunks = [dict(list(hashed_data.items())[i:i+6]) for i in range(0, len(hashed_data), 6)]
        logger.info(f"Data split into {len(chunks)} chunks")

        for i, chunk in enumerate(chunks):
            logger.debug(f"Sending chunk {i+1}: {chunk}")
            lora_manager.send_data(chunk)
            if i < len(chunks) - 1:  # If not the last chunk
                sleep(60)  # Wait 60 seconds between transmissions

        logger.info(f"Successfully sent {len(chunks)} LoRa packets")
    except Exception as e:
        logger.error(f"Error in send_lora_data: {e}")
    finally:
        lora_manager.close()
