

Set Up and Run the Bridge:
   - Make the setup script executable:
     ```
     chmod +x setup_mqtt_bridge.sh
     ```
   - Set the GOOGLE_APPLICATION_CREDENTIALS environment variable:
     ```
     export GOOGLE_APPLICATION_CREDENTIALS="/home/bnsoh652/crop2cloud24-4b30f843e1cf.json"
     ```
   - Run the setup script:
     ```
     ./setup_mqtt_bridge.sh
     ```

Monitor the Bridge:
   To view the logs and monitor the bridge:
   ```
   sudo journalctl -u mqtt-bridge -f
   ```

