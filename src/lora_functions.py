import json
import logging
from time import sleep
from rak811.rak811_v3 import Rak811
import os
from dotenv import load_dotenv
from utils import get_sensor_hash

load_dotenv()

logger = logging.getLogger(__name__)

class LoRaManager:
    def __init__(self, config):
        self.lora = Rak811()
        self.config = config
        self.setup_lora()

    def setup_lora(self):
        try:
            self.lora.set_config('lora:work_mode:0')
            self.lora.set_config('lora:join_mode:1')
            self.lora.set_config(f'lora:region:{self.config["region"]}')
            self.lora.set_config(f'lora:dev_addr:{os.getenv("DEV_ADDR")}')
            self.lora.set_config(f'lora:apps_key:{os.getenv("APPS_KEY")}')
            self.lora.set_config(f'lora:nwks_key:{os.getenv("NWKS_KEY")}')
            self.lora.set_config(f'lora:dr:{self.config["data_rate"]}')
            
            self.lora.join()
            logger.info("Joined LoRaWAN network")
        except Exception as e:
            logger.error(f"Error setting up LoRa: {e}")
            raise

    def send_data(self, data):
        try:
            json_payload = json.dumps(data)
            payload = json_payload.encode('utf-8')
            self.lora.send(payload)
            logger.info(f"Sent payload: {json_payload}")
        except Exception as e:
            logger.error(f"Error sending LoRa data: {e}")
            raise

    def close(self):
        try:
            self.lora.close()
            logger.info("LoRa connection closed")
        except Exception as e:
            logger.error(f"Error closing LoRa connection: {e}")

def send_lora_data(data, config, sensor_metadata):
    lora_manager = LoRaManager(config)
    
    try:
        # Convert full sensor names to hashes
        hashed_data = {get_sensor_hash(k, sensor_metadata): v for k, v in data.items() if get_sensor_hash(k, sensor_metadata)}
        
        # Split data into chunks of 5 key-value pairs (leaving room for timestamp)
        chunks = [dict(list(hashed_data.items())[i:i+5]) for i in range(0, len(hashed_data), 5)]
        
        for chunk in chunks:
            # Add timestamp to each chunk
            chunk['time'] = data['TIMESTAMP'].strftime('%Y%m%d%H%M%S')
            lora_manager.send_data(chunk)
            sleep(10)  # Wait 10 seconds between transmissions
        
        logger.info(f"Sent {len(chunks)} LoRa packets")
    except Exception as e:
        logger.error(f"Error in send_lora_data: {e}")
    finally:
        lora_manager.close()