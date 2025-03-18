# SPDX-FileCopyrightText: 2024 Davíð Berman <davidjberman@gmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import argparse
import sqlite3


# Function to update a specific cell in the database
def update_db_cell(
    db_name, table_name, col_to_change, col_name, col_name_value, new_value
):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # Construct and execute the SQL update query
    query = f"UPDATE {table_name} SET {col_to_change} = ? WHERE {col_name} = ?"
    cursor.execute(query, (new_value, col_name_value))

    conn.commit()
    conn.close()
    print(
        f"Updated {col_to_change} to {new_value} for {col_name} = {col_name_value} in table {table_name}"
    )


# Main function to handle command-line arguments
def main():
    parser = argparse.ArgumentParser(
        description="Update a specific cell in the database."
    )

    # Required arguments
    parser.add_argument("--db", required=True, help="Database name")
    parser.add_argument("--table", required=True, help="Table name")
    parser.add_argument("--colchange", required=True, help="Column to change")
    parser.add_argument(
        "--colname", required=True, help="Column name to identify the row"
    )
    parser.add_argument(
        "--colnamerow", required=True, help="Value of the identifying column"
    )
    parser.add_argument("--newval", required=True, help="New value to set")

    args = parser.parse_args()

    try:
        # Call the update function with the provided arguments
        update_db_cell(
            args.db,
            args.table,
            args.colchange,
            args.colname,
            args.colnamerow,
            args.newval,
        )
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
