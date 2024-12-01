#!/usr/bin/env python3

import sqlite3
import argparse
import math
import datetime
from datetime import timedelta
import sys
import time

def calculate_sunrise_sunset(date, latitude, longitude):
    """Calculate the sunrise and sunset times for the given date and location."""
    # Constants
    zenith = 90.833  # Official zenith for sunrise/sunset

    # Calculate day of the year
    N = date.timetuple().tm_yday

    # Convert longitude to hour value and calculate an approximate time
    lng_hour = longitude / 15

    # Sunrise calculations
    t_rise = N + ((6 - lng_hour) / 24)
    M_rise = (0.9856 * t_rise) - 3.289
    L_rise = (M_rise + (1.916 * math.sin(math.radians(M_rise))) + (0.020 * math.sin(math.radians(2 * M_rise))) + 282.634) % 360
    RA_rise = (math.degrees(math.atan(0.91764 * math.tan(math.radians(L_rise))))) % 360
    Lquadrant_rise  = (math.floor(L_rise/90)) * 90
    RAquadrant_rise = (math.floor(RA_rise/90)) * 90
    RA_rise = RA_rise + (Lquadrant_rise - RAquadrant_rise)
    RA_rise = RA_rise / 15
    sinDec_rise = 0.39782 * math.sin(math.radians(L_rise))
    cosDec_rise = math.cos(math.asin(sinDec_rise))
    cosH_rise = (math.cos(math.radians(zenith)) - (sinDec_rise * math.sin(math.radians(latitude)))) / (cosDec_rise * math.cos(math.radians(latitude)))
    if cosH_rise > 1:
        return None, None  # Sun never rises on this location (on the specified date)
    H_rise = 360 - math.degrees(math.acos(cosH_rise))
    H_rise = H_rise / 15
    T_rise = H_rise + RA_rise - (0.06571 * t_rise) - 6.622
    UT_rise = (T_rise - lng_hour) % 24
    sunrise_time = datetime.datetime.combine(date, datetime.time(0, 0, 0)) + timedelta(hours=UT_rise)

    # Sunset calculations
    t_set = N + ((18 - lng_hour) / 24)
    M_set = (0.9856 * t_set) - 3.289
    L_set = (M_set + (1.916 * math.sin(math.radians(M_set))) + (0.020 * math.sin(math.radians(2 * M_set))) + 282.634) % 360
    RA_set = (math.degrees(math.atan(0.91764 * math.tan(math.radians(L_set))))) % 360
    Lquadrant_set  = (math.floor(L_set/90)) * 90
    RAquadrant_set = (math.floor(RA_set/90)) * 90
    RA_set = RA_set + (Lquadrant_set - RAquadrant_set)
    RA_set = RA_set / 15
    sinDec_set = 0.39782 * math.sin(math.radians(L_set))
    cosDec_set = math.cos(math.asin(sinDec_set))
    cosH_set = (math.cos(math.radians(zenith)) - (sinDec_set * math.sin(math.radians(latitude)))) / (cosDec_set * math.cos(math.radians(latitude)))
    if cosH_set < -1:
        return None, None  # Sun never sets on this location (on the specified date)
    H_set = math.degrees(math.acos(cosH_set))
    H_set = H_set / 15
    T_set = H_set + RA_set - (0.06571 * t_set) - 6.622
    UT_set = (T_set - lng_hour) % 24
    sunset_time = datetime.datetime.combine(date, datetime.time(0, 0, 0)) + timedelta(hours=UT_set)

    return sunrise_time, sunset_time

def calculate_events(current_time, latitude, longitude, offset):
    """Calculate the last event, next event, and the event after."""
    # Collect events over a 3-day window
    events = []
    for day_offset in range(-1, 4):
        date = current_time.date() + timedelta(days=day_offset)
        sunrise_time, sunset_time = calculate_sunrise_sunset(date, latitude, longitude)

        # Adjust for offset
        if sunrise_time:
            sunrise_time += timedelta(minutes=offset)
            events.append(('OFF', sunrise_time))
        if sunset_time:
            sunset_time -= timedelta(minutes=offset)
            events.append(('ON', sunset_time))

    # Sort events by time
    events.sort(key=lambda x: x[1])

    # Remove consecutive duplicate actions
    filtered_events = []
    last_action = None
    for event in events:
        if event[0] != last_action:
            filtered_events.append(event)
            last_action = event[0]
        else:
            continue  # Skip duplicate action

    # Find last event before current time
    last_event = None
    next_event = None
    event_after = None
    current_state = 'OFF'  # Default state

    for event in filtered_events:
        if event[1] <= current_time:
            last_event = event
            current_state = event[0]  # Update current state
        elif not next_event:
            next_event = event
        elif not event_after:
            event_after = event

    return last_event, next_event, event_after, current_state

def write_to_db(styring_db, device_id, last_event, next_event, current_state):
    conn = sqlite3.connect(styring_db)
    cursor = conn.cursor()

    # Prepare data to update
    timestamp_format = "%Y-%m-%dT%H:%M:%S.%f"  # ISO 8601 format with microseconds

    lastastrotime = last_event[1].strftime(timestamp_format) if last_event else None
    lasastroOP = last_event[0] if last_event else None
    nextastrotime = next_event[1].strftime(timestamp_format) if next_event else None
    nextastroOP = next_event[0] if next_event else None
    astrostate = current_state  # Current state of the lights (ON/OFF)

    # Update the database
    try:
        cursor.execute("""
            UPDATE heimtaugaskapar
            SET lastastrotime = ?,
                lasastroOP = ?,
                nextastrotime = ?,
                nextastroOP = ?,
                astrostate = ?
            WHERE id = ?
        """, (lastastrotime, lasastroOP, nextastrotime, nextastroOP, astrostate, device_id))
        conn.commit()
    except sqlite3.Error as e:
        print(f"An error occurred while updating the database for {device_id}: {e}")
    finally:
        conn.close()

def get_all_devices(styring_db):
    """Retrieve all devices from the database."""
    conn = sqlite3.connect(styring_db)
    conn.row_factory = sqlite3.Row  # Enable dict-like access
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM heimtaugaskapar")
        rows = cursor.fetchall()
        devices = [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"An error occurred while fetching devices: {e}")
        devices = []
    finally:
        conn.close()
    return devices

def print_event_str(label, event):
    """Return the event string instead of printing."""
    if event and event[1]:
        return f'{label}: {event[0]} @ {event[1].strftime("%d%b %H:%M:%S")}'
    else:
        return f'{label}: {event[0] if event else "No event"}'

def process_device(device_info, current_time, args, styring_db):
    """Process a single device."""
    messages = []
    device_id = device_info['id']
    latitude = device_info.get('lat')
    longitude = device_info.get('lon')

    if latitude is None or longitude is None:
        msg = f"Device '{device_id}' does not have latitude and longitude information."
        messages.append(msg)
    else:
        # Convert latitude and longitude to floats
        latitude = float(latitude)
        longitude = float(longitude)

        # Calculate events
        last_event, next_event, event_after, current_state = calculate_events(
            current_time, latitude, longitude, args.offset)

        if args.verbose:
            messages.append(f"\nDevice ID: {device_id}")
            messages.append(f"It is now {current_time.strftime('%d%b %H:%M:%S')} UTC -- The Lights are {current_state}")
            messages.append(f"The configured offset is: {args.offset} minutes")
            messages.append(print_event_str('Last event', last_event))
            messages.append(print_event_str('Next event', next_event))
            messages.append(print_event_str('Event after', event_after))

        if args.write2db:
            write_to_db(styring_db, device_id, last_event, next_event, current_state)

    return messages

# Main execution starts here
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calculate events and update the database.")
    parser.add_argument("--id", help="The device ID for which to calculate the event data.")
    parser.add_argument("--test", nargs='*', help="Test mode with a specific date and time (e.g., Jun 16 12:34:56)")
    parser.add_argument("--write2db", action="store_true", help="Write the results to the styring.db database.")
    parser.add_argument("--verbose", action="store_true", help="Show detailed output for each device.")
    parser.add_argument("--offset", type=int, default=0, help="Offset in minutes for lights ON/OFF times")
    args = parser.parse_args()

    styring_db = "styring.db"

    if args.write2db and args.test:
        print("Error: The --write2db flag cannot be used with --test.")
        sys.exit(1)

    if args.test:
        test_time_str = ' '.join(args.test)
        try:
            current_time = datetime.datetime.strptime(test_time_str, "%b %d %H:%M:%S")
        except ValueError:
            try:
                current_time = datetime.datetime.strptime(test_time_str, "%b %d")
                current_time = current_time.replace(hour=0, minute=0, second=0)
            except ValueError:
                print('Invalid date format. Please use "MON dd" or "MON dd HH:MM:SS"')
                exit(1)
        current_time = current_time.replace(year=datetime.datetime.utcnow().year)
    else:
        current_time = datetime.datetime.utcnow()

    try:
        if args.id:
            # Fetch the device information from the database
            conn = sqlite3.connect(styring_db)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM heimtaugaskapar WHERE id = ?", (args.id,))
            row = cursor.fetchone()
            if row:
                devices = [dict(row)]
            else:
                print(f"No device found with ID {args.id}")
                devices = []
            conn.close()
        else:
            devices = get_all_devices(styring_db)

        device_count = len(devices)
        device_index = 0
        output_messages = []

        if args.write2db:
            # Loop indefinitely when --write2db is specified
            while True:
                current_time = datetime.datetime.utcnow()

                # Process one device at a time
                device_info = devices[device_index]
                messages = process_device(device_info, current_time, args, styring_db)
                output_messages.extend(messages)

                # Wait for 1 second before processing next device
                time.sleep(1)

                # Move to the next device
                device_index = (device_index + 1) % device_count

                # If we've completed a full cycle, output the messages and reset
                if device_index == 0:
                    if args.verbose:
                        # Output the collected messages
                        for msg in output_messages:
                            print(msg)
                    else:
                        # Output a single line with timestamp
                        timestamp = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]
                        print(f"{timestamp} - Updated event data for all devices.")
                    # Clear the messages
                    output_messages = []
        else:
            # Process devices once and exit
            for device_info in devices:
                messages = process_device(device_info, current_time, args, styring_db)
                for msg in messages:
                    print(msg)

    except KeyboardInterrupt:
        print("\nScript terminated by user.")
        sys.exit(0)
