import sqlite3
import time
import subprocess

DB_NAME = "styring.db"  # Database name
CHECK_INTERVAL = 1  # Interval between processing devices in seconds


def update_uxstate(device_id, new_value):
    # fmt: off
    command = [
        "python3", "updateDBcell.py",
        "--db", DB_NAME,
        "--table", "heimtaugaskapar",
        "--colchange", "uxstate",
        "--colname", "id",
        "--colnamerow", device_id,
        "--newval", new_value,
    ]
    # fmt: on
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error updating uxstate for device {device_id}: {result.stderr}")
    else:
        print(f"Updated uxstate for device {device_id} to {new_value}.")


def main():
    while True:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        # Fetch all devices from the heimtaugaskapar table
        cursor.execute(
            "SELECT id, astroman, astrostate, outputstate FROM heimtaugaskapar"
        )
        devices = cursor.fetchall()

        conn.close()

        for device in devices:
            device_id = device[0]
            astroman = device[1]
            astrostate = device[2]
            outputstate = device[3]

            if astroman == "MANUAL":
                # Do nothing and move to the next device
                print(f"Device {device_id} is in MANUAL mode. Skipping.")
                continue
            elif astroman == "ASTRO":
                # Update uxstate to match astrostate
                update_uxstate(device_id, astrostate)

                # Check if astrostate is not the same as outputstate
                if astrostate != outputstate:
                    # Determine the action based on astrostate
                    if astrostate in ["ON", "OFF"]:
                        turn_state = astrostate
                        # Use apiTurn.py to send the command
                        # fmt: off
                        command = [
                            "python3", "apiTurn.py",
                            "--id", device_id,
                            "--turn", turn_state,
                        ]
                        # fmt: on
                        result = subprocess.run(command, capture_output=True, text=True)
                        if result.returncode != 0:
                            print(
                                f"Error turning {turn_state} device {device_id}: {result.stderr}"
                            )
                        else:
                            print(
                                f"Turned {turn_state} device {device_id}: {result.stdout}"
                            )
                    else:
                        print(
                            f"Device {device_id} has invalid astrostate '{astrostate}'. Skipping."
                        )
                else:
                    print(
                        f"Device {device_id}: astrostate matches outputstate. No action needed."
                    )
            else:
                print(
                    f"Device {device_id} has invalid astroman value '{astroman}'. Skipping."
                )

            # Wait before processing the next device
            time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
