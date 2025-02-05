import sqlite3
import time
import subprocess

DB_NAME = "styring.db"  # Database name
CHECK_INTERVAL = 10  # Minimum interval between API requests in seconds


# Function to get all devices from the heimtaugaskapar table
def get_all_devices():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    query = "SELECT id FROM heimtaugaskapar"
    cursor.execute(query)
    devices = cursor.fetchall()

    conn.close()

    return [device[0] for device in devices]


# Function to call apiState.py for inputstate or outputstate
def check_state(device_id, var):
    command = ["python3", "apiState.py", "--id", device_id, "--var", var]

    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error checking {var} for device {device_id}: {result.stderr}")
    else:
        print(f"{var} checked for device {device_id}: {result.stdout}")


# Function to compare inputstate and outputstate and update localremote
def update_localremote(device_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Get inputstate and outputstate
    cursor.execute(
        "SELECT inputstate, outputstate FROM heimtaugaskapar WHERE id = ?", (device_id,)
    )
    row = cursor.fetchone()

    if row:
        inputstate = row[0]
        outputstate = row[1]

        if inputstate != outputstate:
            localremote = "LOCAL"
        else:
            localremote = "REMOTE"

        # Update localremote
        cursor.execute(
            "UPDATE heimtaugaskapar SET localremote = ? WHERE id = ?",
            (localremote, device_id),
        )
        conn.commit()
        print(f"Updated localremote for device {device_id} to {localremote}")
    else:
        print(f"Device {device_id} not found in database.")

    conn.close()


# Main loop that checks both inputstate and outputstate for each device
def main():
    while True:
        devices = get_all_devices()

        for device_id in devices:
            # Check inputstate
            check_state(device_id, "inputstate")
            time.sleep(CHECK_INTERVAL)

            # Check outputstate
            check_state(device_id, "outputstate")
            time.sleep(CHECK_INTERVAL)

            # Compare inputstate and outputstate, update localremote
            update_localremote(device_id)

            # Wait before processing the next device
            # Optional: Uncomment the following line if you want an additional delay
            # time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
