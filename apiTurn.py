import argparse
import sqlite3
import requests
import os
import subprocess
from dotenv import load_dotenv, get_key

# Load environment variables
load_dotenv()

# Explicitly get USERNAME from the .env file directly
USERNAME = get_key(".env", "USERNAME")
PASSWORD = os.getenv("PASSWORD")

DB_NAME = 'styring.db'  # Update this to your actual database name if different
TIMEOUT = 5  # Timeout for API requests in seconds
RETRY_LIMIT = 3  # Number of times to retry the API request

# Function to get data from SQLite DB by device ID
def get_device_info_by_id(device_id: str) -> dict[str, str]:
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
def get_device_info_by_hs(hs: str) -> dict[str, str]:
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

# Function to turn on/off the output
def turn_output(device_info: dict[str, str], state: str) -> dict[str, str]:
    ip = device_info['ip']
    pin = device_info['output_pin']

    # Construct the URL with plain-text credentials in the query string
    url = f"http://{ip}/cgi-bin/io_state?username={USERNAME}&password={PASSWORD}&pin={pin}&state={state.lower()}"

    # Print the URL without exposing the password
    print(f"API URL: http://{ip}/cgi-bin/io_state?username={USERNAME}&pin={pin}&state={state.lower()} [password hidden]")
    
    # Send the request
    for attempt in range(RETRY_LIMIT):
        try:
            response = requests.get(url, timeout=TIMEOUT)

            if response.status_code == 200:
                print(f"Successfully turned {state.upper()} {pin} for device with IP {ip}")
                return {"status": "success", "ip": ip, "pin": pin}
            else:
                print(f"Failed to send request. Status code: {response.status_code}")
                return {"status": "failure", "ip": ip, "pin": pin, "reason": "HTTP error", "code": response.status_code}

        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt+1}/{RETRY_LIMIT}: Error communicating with {ip}: {e}")

    return {"status": "failure", "ip": ip, "pin": pin, "reason": "max retries exceeded"}

# Function to check the pin state (input or output) via API and update the database
def check_and_update_pin_state(device_info: str, var: str) -> None:
    # Construct the URL for checking the pin state
    ip = device_info['ip']
    pin = device_info['input_pin'] if var == 'inputstate' else device_info['output_pin']

    url = f"http://{ip}/cgi-bin/io_value?username={USERNAME}&password={PASSWORD}&pin={pin}"
    
    # Send the request
    try:
        response = requests.get(url, timeout=TIMEOUT)
        if response.status_code == 200:
            pin_state = response.text.strip()  # Get the pin state (0 or 1)
            new_value = 'ON' if pin_state == '1' else 'OFF'
            print(f"{var.capitalize()} for {pin} at IP {ip}: {new_value}")

            # Update the database using updateDBcell.py script
            update_db(device_info['id'], var, new_value)
        else:
            print(f"Failed to check {var}. Status code: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"Error communicating with {ip} for {var}: {e}")

# Function to update the database using updateDBcell.py script
def update_db(device_id: str, col_to_change: str, new_value: str) -> None:
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
def main() -> None:
    parser = argparse.ArgumentParser(description="Turn device output on or off and verify the state change.")

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--id', help="ID of the device")
    group.add_argument('--hs', help="HS number of the device")

    parser.add_argument('--turn', choices=['ON', 'OFF', 'on', 'off'], required=True, help="Turn output ON or OFF")

    args = parser.parse_args()

    try:
        if args.id:
            device_info = get_device_info_by_id(args.id)
        elif args.hs:
            device_info = get_device_info_by_hs(args.hs)

        # Turn the output on or off
        result = turn_output(device_info, args.turn.upper())

        # If the API call was successful, check and update both outputstate and inputstate
        if result['status'] == 'success':
            check_and_update_pin_state(device_info, 'outputstate')
            check_and_update_pin_state(device_info, 'inputstate')

    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    main()
