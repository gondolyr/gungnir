# SPDX-FileCopyrightText: 2024 Davíð Berman <davidjberman@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import sqlite3
import subprocess
from datetime import datetime

from flask import Flask, redirect, render_template, request, url_for

app = Flask(__name__)

DATABASE = "styring.db"


def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # Enable dict-like access to rows
    return conn


# Custom Jinja2 filter to format datetime strings
@app.template_filter("datetimeformat")
def datetimeformat(value):
    if value:
        try:
            # Parse the datetime string from the database
            dt = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%f")
            # Format it into a human-readable format
            return dt.strftime("%d.%m.%Y %H:%M:%S")
        except ValueError:
            # Handle cases where microseconds might be missing
            dt = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")
            return dt.strftime("%d.%m.%Y %H:%M:%S")
    else:
        return "N/A"


@app.route("/")
def index():
    conn = get_db_connection()
    devices = conn.execute("SELECT * FROM heimtaugaskapar").fetchall()
    conn.close()

    # Organize devices by hverfi
    hverfi_dict = {}
    for device in devices:
        hverfi = device["hverfi"]
        if hverfi not in hverfi_dict:
            hverfi_dict[hverfi] = []
        hverfi_dict[hverfi].append(device)

    return render_template("index.html", hverfi_dict=hverfi_dict)


@app.route("/update_astroman", methods=["POST"])
def update_astroman():
    device_id = request.form["device_id"]
    new_mode = request.form["astroman"]
    conn = get_db_connection()
    conn.execute(
        "UPDATE heimtaugaskapar SET astroman = ? WHERE id = ?", (new_mode, device_id)
    )
    conn.commit()
    conn.close()
    return redirect(url_for("index"))


@app.route("/update_uxstate", methods=["POST"])
def update_uxstate():
    device_id = request.form["device_id"]
    new_state = request.form["uxstate"]
    conn = get_db_connection()

    # Get current outputstate
    device = conn.execute(
        "SELECT outputstate FROM heimtaugaskapar WHERE id = ?", (device_id,)
    ).fetchone()
    if device is not None:
        current_outputstate = device["outputstate"]
        if new_state != current_outputstate:
            # Call apiTurn.py with appropriate arguments
            result = subprocess.run(
                ["python3", "apiTurn.py", "--id", device_id, "--turn", new_state],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                print(f"Error executing apiTurn.py: {result.stderr}")
                # Optionally, handle the error (e.g., flash message to the user)
            else:
                print(f"apiTurn.py output: {result.stdout}")
        else:
            print(
                f"No action needed for device {device_id}. Desired state '{new_state}' matches current outputstate."
            )
    else:
        print(f"Device {device_id} not found in database.")

    # Update uxstate in database
    conn.execute(
        "UPDATE heimtaugaskapar SET uxstate = ? WHERE id = ?", (new_state, device_id)
    )
    conn.commit()
    conn.close()
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5051)
