from flask import Flask, render_template_string, abort, request, redirect, url_for, Response
import sqlite3
import csv
import io
import argparse

app = Flask(__name__)

# HTML template for rendering tables and data
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<title>{{ table_name | capitalize if table_name else "Tables" }}</title>
<style>
table, th, td {
  border: 1px solid black;
  border-collapse: collapse;
}
th, td {
  padding: 5px;
  text-align: left;
}
</style>
</head>
<body>
{% if not table_name %}
<h2>Available Tables</h2>
<ul>
  {% for table in tables %}
  <li>
    <a href="/{{ table }}">{{ table }}</a> - 
    <a href="/download/{{ table }}/csv">csv</a>
  </li>
  {% endfor %}
</ul>
{% else %}
<h2>{{ table_name | capitalize }}</h2>
<table>
  <tr>
    {% for column in columns %}
    <th>{{ column }}</th>
    {% endfor %}
  </tr>
  {% for row in rows %}
  <tr>
    {% for cell in row %}
    <td>{{ cell }}</td>
    {% endfor %}
  </tr>
  {% endfor %}
</table>
{% endif %}
</body>
</html>
"""

# Function to connect to your database
def get_db_connection(db_name: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_name)
    conn.row_factory = sqlite3.Row
    return conn

# Route to display tables and data
@app.route('/', defaults={'table_name': None})
@app.route('/<table_name>')
def show_table(table_name: str) -> str:
    conn = get_db_connection(app.config['DB_NAME'])
    cur = conn.cursor()
    
    if table_name is None:
        # List all tables
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cur.fetchall()]
        conn.close()
        return render_template_string(HTML_TEMPLATE, tables=tables)
    else:
        # Show data from the specified table
        try:
            cur.execute(f'SELECT * FROM "{table_name}" LIMIT 1000')
        except sqlite3.OperationalError:
            conn.close()
            abort(404)
        rows = cur.fetchall()
        columns = [description[0] for description in cur.description]
        conn.close()
        return render_template_string(HTML_TEMPLATE, table_name=table_name, rows=rows, columns=columns)

# Route to download table as CSV
@app.route('/download/<table_name>/csv')
def download_csv(table_name: str) -> Response:
    conn = get_db_connection(app.config['DB_NAME'])
    cur = conn.cursor()
    try:
        cur.execute(f'SELECT * FROM "{table_name}"')
    except sqlite3.OperationalError:
        conn.close()
        abort(404)
    rows = cur.fetchall()
    columns = [description[0] for description in cur.description]
    conn.close()

    # Create CSV in-memory file
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(columns)
    for row in rows:
        writer.writerow(row)
    output.seek(0)
    return Response(output, mimetype='text/csv',
                    headers={"Content-Disposition": f"attachment;filename={table_name}.csv"})

if __name__ == '__main__':
    # Argument parser for database name and port
    parser = argparse.ArgumentParser(description='Run Flask app with SQLite database.')
    parser.add_argument('--db', type=str, required=True, help='The SQLite database file to use')
    parser.add_argument('--port', type=int, default=5000, help='The port to run the Flask app on (default is 5000)')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Pass the database name as a Flask app config
    app.config['DB_NAME'] = args.db
    
    # Run the Flask app with the specified port
    app.run(host='0.0.0.0', port=args.port)
