import argparse
import sqlite3
import requests
import os
import subprocess
from dotenv import load_dotenv, get_key

# Load environment variables
load_dotenv()

# Explicitly get USERNAME from the .env file
USERNAME = get_key(".env", "USERNAME")
PASSWORD = os.getenv("PASSWORD")

DB_NAME = 'styring.db'  # Update this to your actual database name if different
TIMEOUT = 5  # Timeout for API requests in seconds
RETRY_LIMIT = 3  # Number of times to retry the API request

# Function to get data from SQLite DB by device ID
def get_device_info_by_id(device_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    query = "SELECT id, tsip, inputpin, outputpin FROM heimtaugaskapar WHERE id = ?"
    cursor.execute(query, (device_id,))
    result = cursor.fetchone()

    conn.close()

    if result:
        return {'id': result[0], 'ip': result[1], 'input_pin': result[2], 'output_pin': result[3]}
    else:
        raise ValueError(f"No device found with id {device_id}")

# Function to get data from SQLite DB by HS number
def get_device_info_by_hs(hs):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    query = "SELECT id, tsip, inputpin, outputpin FROM heimtaugaskapar WHERE hs = ?"
    cursor.execute(query, (hs,))
    result = cursor.fetchone()

    conn.close()

    if result:
        return {'id': result[0], 'ip': result[1], 'input_pin': result[2], 'output_pin': result[3]}
    else:
        raise ValueError(f"No device found with hs {hs}")

# Function to get output or input pin by IP address
def get_device_info_by_ip(ip):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    query = "SELECT id, inputpin, outputpin FROM heimtaugaskapar WHERE tsip = ?"
    cursor.execute(query, (ip,))
    result = cursor.fetchone()

    conn.close()

    if result:
        return {'id': result[0], 'input_pin': result[1], 'output_pin': result[2]}
    else:
        raise ValueError(f"No device found with IP {ip}")

# Function to check the state of a pin via API (input or output based on --var flag)
def check_pin_state(device_info, var):
    ip = device_info['ip']
    
    # Select pin based on --var flag (either input_pin or output_pin)
    pin = device_info['input_pin'] if var == 'inputstate' else device_info['output_pin']

    # Construct the URL with plain-text credentials in the query string
    url = f"http://{ip}/cgi-bin/io_value"
    payload = {
        "username": USERNAME,
        "password": PASSWORD,
        "pin": pin,
    }

    # Send the request
    for attempt in range(RETRY_LIMIT):
        try:
            response = requests.get(url, params=payload, timeout=TIMEOUT)

            if response.status_code == 200:
                pin_state = response.text.strip()  # Get the pin state from the API response (0 or 1)
                print(f"Pin state for {pin} at IP {ip}: {pin_state}")
                return pin_state
            else:
                print(f"Failed to send request. Status code: {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt+1}/{RETRY_LIMIT}: Error communicating with {ip}: {e}")

    return None

# Function to update the DB using updateDBcell.py script
def update_db(device_id, col_to_change, new_value):
    command = [
        "python3", "updateDBcell.py",
        "--db", DB_NAME,
        "--table", "heimtaugaskapar",
        "--colchange", col_to_change,
        "--colname", "id",
        "--colnamerow", device_id,
        "--newval", new_value
    ]
    
    result = subprocess.run(command, capture_output=True, text=True)
    print(result.stdout)

# Main function to handle command-line arguments
def main():
    parser = argparse.ArgumentParser(description="Check device pin state and update the database.")

    # Mutually exclusive arguments for selecting the device
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--id', help="ID of the device")
    group.add_argument('--hs', help="HS number of the device")
    group.add_argument('--ip', help="IP address of the device")

    # Column to update in the DB, now supporting both inputstate and outputstate
    parser.add_argument('--var', choices=['inputstate', 'outputstate'], required=True, help="Variable to update (e.g., inputstate or outputstate)")

    args = parser.parse_args()

    try:
        # Get device information based on the provided arguments
        if args.id:
            device_info = get_device_info_by_id(args.id)
        elif args.hs:
            device_info = get_device_info_by_hs(args.hs)
        elif args.ip:
            device_info = get_device_info_by_ip(args.ip)
            device_info['ip'] = args.ip  # IP is directly provided, no need to look up

        # Check the pin state (input or output) via API
        pin_state = check_pin_state(device_info, args.var)

        # Update the database if pin_state is retrieved successfully
        if pin_state is not None:
            new_value = 'ON' if pin_state == '1' else 'OFF'
            update_db(device_info['id'], args.var, new_value)
        else:
            print("Failed to retrieve pin state.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    main()
