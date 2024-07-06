import json
import time
import random
from rak811.rak811_v3 import Rak811
from .utils import setup_logger, get_sensor_hash

logger = setup_logger("lora_functions", "lora_functions.log")

MAX_RETRIES = 3
RETRY_DELAY = 60  # 1 minute

class LoRaManager:
    def __init__(self, lora_config):
        self.lora = None
        self.config = lora_config

    def setup_lora(self):
        for attempt in range(MAX_RETRIES):
            try:
                self.lora = Rak811()
                logger.info("Setting LoRa work mode...")
                self.lora.set_config("lora:work_mode:0")
                logger.info("Setting LoRa join mode...")
                self.lora.set_config("lora:join_mode:1")
                logger.info(f"Setting LoRa region: {self.config['region']}")
                self.lora.set_config(f'lora:region:{self.config["region"]}')
                logger.info("Setting LoRa device address...")
                self.lora.set_config(f'lora:dev_addr:{self.config["dev_addr"]}')
                logger.info("Setting LoRa application session key...")
                self.lora.set_config(f'lora:apps_key:{self.config["apps_key"]}')
                logger.info("Setting LoRa network session key...")
                self.lora.set_config(f'lora:nwks_key:{self.config["nwks_key"]}')
                logger.info(f"Setting LoRa data rate: {self.config['data_rate']}")
                self.lora.set_config(f'lora:dr:{self.config["data_rate"]}')
                logger.info("Joining LoRaWAN network...")
                self.lora.join()
                logger.info("Joined LoRaWAN network successfully")
                return
            except Exception as e:
                logger.error(f"Error setting up LoRa (Attempt {attempt + 1}/{MAX_RETRIES}): {e}")
                if attempt < MAX_RETRIES - 1:
                    logger.info(f"Retrying in {RETRY_DELAY} seconds...")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error("Max retries reached. Unable to set up LoRa.")
                    raise

    def send_data(self, data):
        for attempt in range(MAX_RETRIES):
            try:
                json_payload = json.dumps(data)
                payload = json_payload.encode("utf-8")
                self.lora.send(payload)
                logger.info(f"Sent payload: {json_payload}")
                return
            except Exception as e:
                logger.error(f"Error sending LoRa data (Attempt {attempt + 1}/{MAX_RETRIES}): {e}")
                if attempt < MAX_RETRIES - 1:
                    logger.info(f"Retrying in {RETRY_DELAY} seconds...")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error("Max retries reached. Unable to send LoRa data.")
                    raise

    def close(self):
        if self.lora:
            try:
                self.lora.close()
                logger.info("LoRa connection closed successfully")
            except Exception as e:
                logger.error(f"Error closing LoRa connection: {e}")

def send_lora_data(data, config, sensor_metadata, clip_floats=False):
    logger.info("Initializing LoRa data transmission")
    logger.debug(f"Original data to be sent: {json.dumps(data, default=str)}")

    required_keys = ['lora', 'schedule']
    for key in required_keys:
        if key not in config:
            raise KeyError(f"Required configuration key '{key}' is missing")

    if 'transmission_window' not in config['schedule'] or 'min_interval' not in config['schedule']:
        raise KeyError("'transmission_window' and 'min_interval' must be specified in the 'schedule' configuration")

    lora_manager = LoRaManager(config['lora'])

    try:
        lora_manager.setup_lora()

        hashed_data = {
            get_sensor_hash(k, sensor_metadata): v
            for k, v in data.items()
            if get_sensor_hash(k, sensor_metadata) and k != "TIMESTAMP"
        }
        
        hashed_data["time"] = data["TIMESTAMP"].strftime("%Y%m%d%H%M%S")
        
        if "BatV" in data:
            hashed_data["BatV"] = data["BatV"]

        if clip_floats:
            hashed_data = {k: round(v, 2) if isinstance(v, float) else v for k, v in hashed_data.items()}

        logger.debug(f"Hashed data: {json.dumps(hashed_data, default=str)}")

        chunks = [dict(list(hashed_data.items())[i:i+6]) for i in range(0, len(hashed_data), 6)]
        logger.info(f"Data split into {len(chunks)} chunks")

        transmission_window = config['schedule']['transmission_window']
        min_interval = config['schedule']['min_interval']

        max_delay = (transmission_window - (len(chunks) - 1) * min_interval) / len(chunks)

        start_time = time.time()

        for i, chunk in enumerate(chunks):
            if "time" not in chunk:
                chunk["time"] = hashed_data["time"]
            
            if i > 0 and "BatV" in chunk:
                del chunk["BatV"]
            
            logger.debug(f"Sending chunk {i+1}: {json.dumps(chunk, default=str)}")
            lora_manager.send_data(chunk)
            
            if i < len(chunks) - 1:
                delay = random.uniform(min_interval, max_delay)
                logger.info(f"Waiting {delay:.2f} seconds before sending next chunk")
                time.sleep(delay)

        total_time = time.time() - start_time
        logger.info(f"Successfully sent {len(chunks)} LoRa packets in {total_time:.2f} seconds")
        
        if total_time > transmission_window:
            logger.warning(f"Total transmission time exceeded window by {total_time - transmission_window:.2f} seconds")
        
    except Exception as e:
        logger.error(f"Error in send_lora_data: {e}")
        raise
    finally:
        lora_manager.close()
