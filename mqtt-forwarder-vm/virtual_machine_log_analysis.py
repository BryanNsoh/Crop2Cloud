import re
from datetime import datetime, timedelta, date
import pandas as pd
import json

def analyze_pubsub_logs(log_file_path):
    successful_publications = []
    message_pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}).*Successfully published message with ID: (\d+)'
    data_pattern = r'Published data: ({.*})'
    device_name_pattern = r'"deviceName": "([^"]+)"'
    decoded_payload_pattern = r'Decoded payload: ({.*})'
    
    with open(log_file_path, 'r') as file:
        content = file.read()
        message_matches = re.finditer(message_pattern, content)
        
        for match in message_matches:
            timestamp = datetime.strptime(match.group(1), '%Y-%m-%d %H:%M:%S,%f')
            message_id = match.group(2)
            
            data_match = re.search(data_pattern, content[max(0, match.start()-5000):match.start()])
            device_name_match = re.search(device_name_pattern, content[max(0, match.start()-5000):match.start()])
            decoded_payload_match = re.search(decoded_payload_pattern, content[max(0, match.start()-5000):match.start()])
            
            if data_match and device_name_match and decoded_payload_match:
                data = json.loads(data_match.group(1))
                device_name = device_name_match.group(1)
                decoded_payload = json.loads(decoded_payload_match.group(1))
                
                sensor_id = data.get('sensor_id', 'Unknown')
                project_name = data.get('project_name', 'Unknown')
                dataset_name = data.get('dataset_name', 'Unknown')
                table_name = data.get('table_name', 'Unknown')
                value = data.get('value', 'Unknown')
                
                successful_publications.append((timestamp, message_id, device_name, sensor_id, project_name, dataset_name, table_name, value, decoded_payload))
    
    return successful_publications

def comprehensive_analysis(publications):
    df = pd.DataFrame(publications, columns=['timestamp', 'message_id', 'device_name', 'sensor_id', 'project_name', 'dataset_name', 'table_name', 'value', 'decoded_payload'])
    df['date'] = df['timestamp'].dt.date
    df['hour'] = df['timestamp'].dt.floor('h')
    
    analysis = {
        'Total Publications': len(df),
        'Date Range': f"{df['timestamp'].min()} to {df['timestamp'].max()}",
        'Total Duration': str(df['timestamp'].max() - df['timestamp'].min()),
        'Daily Breakdown': df.groupby('date').size().reset_index(name='count').to_dict('records'),
        'Hourly Breakdown': df.groupby('hour').size().reset_index(name='count').to_dict('records'),
        'Device Distribution': df['device_name'].value_counts().reset_index(name='count').to_dict('records'),
        'Project Distribution': df['project_name'].value_counts().reset_index(name='count').to_dict('records'),
        'Dataset Distribution': df['dataset_name'].value_counts().reset_index(name='count').to_dict('records'),
        'Table Distribution': df['table_name'].value_counts().reset_index(name='count').to_dict('records'),
        'Sensor Distribution': df['sensor_id'].value_counts().reset_index(name='count').to_dict('records'),
        'Value Statistics': df.groupby('sensor_id')['value'].agg(['mean', 'min', 'max']).reset_index().to_dict('records')
    }
    
    return analysis

def analyze_all_days_fixed(publications):
    df = pd.DataFrame(publications, columns=['timestamp', 'message_id', 'device_name', 'sensor_id', 'project_name', 'dataset_name', 'table_name', 'value', 'decoded_payload'])
    df['date'] = df['timestamp'].dt.date
    
    unique_dates = df['date'].unique()
    daily_analyses = {}

    for date in unique_dates:
        daily_df = df[df['date'] == date]
        analysis = comprehensive_analysis(daily_df)
        daily_analyses[str(date)] = analysis
    
    return daily_analyses

def ensure_serializable(data):
    if isinstance(data, (pd.Timestamp, datetime, date, timedelta)):
        return str(data)
    if isinstance(data, dict):
        return {k: ensure_serializable(v) for k, v in data.items()}
    if isinstance(data, list):
        return [ensure_serializable(item) for item in data]
    return data

def save_as_json(daily_analyses, output_path):
    serializable_data = ensure_serializable(daily_analyses)
    with open(output_path, 'w') as json_file:
        json.dump(serializable_data, json_file, indent=4)
    print(f"Saved JSON data to {output_path}")

def run_log_analysis(log_file_path):
    publications = analyze_pubsub_logs(log_file_path)
    all_days_analysis = analyze_all_days_fixed(publications)
    save_as_json(all_days_analysis, r"C:\Users\bnsoh2\OneDrive - University of Nebraska-Lincoln\Documents\Projects\masters-project\Logger_Lora\mqtt-forwarder-vm\all_days_analysis_output.json")

# Example usage:
log_file_path = r'C:\Users\bnsoh2\OneDrive - University of Nebraska-Lincoln\Documents\Projects\masters-project\Logger_Lora\mqtt-forwarder-vm\concatenated_logs.txt'
run_log_analysis(log_file_path)