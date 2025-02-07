# intrapi.py

from flask import Flask, request, abort, Response, make_response
import sqlite3
import subprocess
import json
from functools import wraps

app = Flask(__name__)

DATABASE = 'styring.db'
SECRET_FILE = 'secret'

def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # Enable dict-like access to rows
    return conn

# Load Id and Secret from the 'secret' file
def load_credentials() -> dict[str, str]:
    credentials = {}
    with open(SECRET_FILE, 'r') as f:
        for line in f:
            if line.strip():  # Skip empty lines
                key, value = line.strip().split(':', 1)
                credentials[key.strip()] = value.strip()
    return credentials

credentials = load_credentials()
AUTH_ID = credentials.get('Id')
AUTH_SECRET = credentials.get('Secret')

# Authentication decorator
def require_auth(func: collections.abc.Callable) -> Response:
    @wraps(func)
    def wrapper(*args, **kwargs):
        client_id = request.headers.get('CF-Access-Client-Id')
        client_secret = request.headers.get('CF-Access-Client-Secret')
        if client_id != AUTH_ID or client_secret != AUTH_SECRET:
            return Response('Unauthorized', status=401)
        return func(*args, **kwargs)
    return wrapper

# Helper function to get device by id or hs
def get_device_by_identifier(identifier: str) -> dict[str, str] | None:
    conn = get_db_connection()
    cursor = conn.cursor()

    # Try to fetch by id (without any modifications)
    cursor.execute("SELECT * FROM heimtaugaskapar WHERE id = ?", (identifier,))
    device = cursor.fetchone()
    if device:
        conn.close()
        return dict(device)

    # Modify the identifier for hs lookup (replace '-' with '_')
    hs_identifier = identifier.replace('-', '_')

    # Try to fetch by hs
    cursor.execute("SELECT * FROM heimtaugaskapar WHERE hs = ?", (hs_identifier,))
    device = cursor.fetchone()
    conn.close()
    if device:
        return dict(device)
    else:
        return None

# New root endpoint that returns the same as '/devices'
@app.route('/', methods=['GET'])
@require_auth
def root() -> Response:
    return get_all_devices()

@app.route('/devices', methods=['GET'])
@require_auth
def get_all_devices() -> Response:
    conn = get_db_connection()
    devices = conn.execute('SELECT * FROM heimtaugaskapar').fetchall()
    conn.close()
    devices_list = [dict(device) for device in devices]
    response_json = json.dumps(devices_list, ensure_ascii=False)
    return Response(response_json, content_type='application/json; charset=utf-8')

@app.route('/devices/<identifier>', methods=['GET'])
@require_auth
def get_device(identifier: str) -> Response:
    device = get_device_by_identifier(identifier)
    if device:
        response_json = json.dumps(device, ensure_ascii=False)
        return Response(response_json, content_type='application/json; charset=utf-8')
    else:
        abort(404, description="Device not found")

@app.route('/devices/<identifier>/state', methods=['GET', 'POST'])
@require_auth
def device_state(identifier: str) -> Response:
    device = get_device_by_identifier(identifier)
    if not device:
        abort(404, description="Device not found")

    if request.method == 'GET':
        # Return the current state
        data = {
            'id': device['id'],
            'state': device['outputstate'],
            'astroman': device['astroman']
        }
        response_json = json.dumps(data, ensure_ascii=False)
        return Response(response_json, content_type='application/json; charset=utf-8')
    elif request.method == 'POST':
        # Check if device is in MANUAL mode
        if device['astroman'] != 'MANUAL':
            response = {'error': 'Device is not in MANUAL mode'}
            response_json = json.dumps(response, ensure_ascii=False)
            return Response(response_json, status=403, content_type='application/json; charset=utf-8')

        # Get the desired state from the request data
        data = request.get_json()
        if not data or 'state' not in data:
            abort(400, description="Missing 'state' in request data")

        new_state = data['state'].upper()
        if new_state not in ['ON', 'OFF']:
            abort(400, description="Invalid state. Must be 'ON' or 'OFF'.")

        # Call apiTurn.py to change the state
        result = subprocess.run(
            ['python3', 'apiTurn.py', '--id', device['id'], '--turn', new_state],
            capture_output=True, text=True
        )

        if result.returncode != 0:
            response = {'error': 'Failed to change device state', 'details': result.stderr}
            response_json = json.dumps(response, ensure_ascii=False)
            return Response(response_json, status=500, content_type='application/json; charset=utf-8')
        else:
            # Update uxstate in the database
            conn = get_db_connection()
            conn.execute('UPDATE heimtaugaskapar SET uxstate = ? WHERE id = ?', (new_state, device['id']))
            conn.commit()
            conn.close()
            response = {'message': f'Device {device["id"]} turned {new_state} successfully'}
            response_json = json.dumps(response, ensure_ascii=False)
            return Response(response_json, content_type='application/json; charset=utf-8')

@app.route('/devices/<identifier>/astroman', methods=['GET', 'POST'])
@require_auth
def device_astroman(identifier: str) -> Response:
    device = get_device_by_identifier(identifier)
    if not device:
        abort(404, description="Device not found")

    if request.method == 'GET':
        data = {
            'id': device['id'],
            'astroman': device['astroman']
        }
        response_json = json.dumps(data, ensure_ascii=False)
        return Response(response_json, content_type='application/json; charset=utf-8')
    elif request.method == 'POST':
        # Get the desired astroman value from the request data
        data = request.get_json()
        if not data or 'astroman' not in data:
            abort(400, description="Missing 'astroman' in request data")

        new_mode = data['astroman'].upper()
        if new_mode not in ['ASTRO', 'MANUAL']:
            abort(400, description="Invalid astroman value. Must be 'ASTRO' or 'MANUAL'.")

        # Update the database
        conn = get_db_connection()
        conn.execute('UPDATE heimtaugaskapar SET astroman = ? WHERE id = ?', (new_mode, device['id']))
        conn.commit()
        conn.close()

        response = {'message': f'Device {device["id"]} astroman set to {new_mode}'}
        response_json = json.dumps(response, ensure_ascii=False)
        return Response(response_json, content_type='application/json; charset=utf-8')

@app.route('/devices/<identifier>/fields/<field_name>', methods=['GET'])
@require_auth
def get_device_field(identifier: str, field_name: str) -> Response:
    device = get_device_by_identifier(identifier)
    if not device:
        abort(404, description="Device not found")

    # Validate the field name
    valid_fields = set(device.keys())
    if field_name not in valid_fields:
        abort(400, description=f"Invalid field name '{field_name}'")

    data = {field_name: device[field_name]}
    response_json = json.dumps(data, ensure_ascii=False)
    return Response(response_json, content_type='application/json; charset=utf-8')

# Endpoint for nextastro
@app.route('/devices/<identifier>/nextastro', methods=['GET'])
@require_auth
def device_nextastro(identifier: str) -> Response:
    device = get_device_by_identifier(identifier)
    if not device:
        abort(404, description="Device not found")

    data = {
        'id': device['id'],
        'nextastrotime': device.get('nextastrotime'),
        'nextastroOP': device.get('nextastroOP')
    }
    response_json = json.dumps(data, ensure_ascii=False)
    return Response(response_json, content_type='application/json; charset=utf-8')

# Endpoint for lastastro
@app.route('/devices/<identifier>/lastastro', methods=['GET'])
@require_auth
def device_lastastro(identifier: str) -> Response:
    device = get_device_by_identifier(identifier)
    if not device:
        abort(404, description="Device not found")

    data = {
        'id': device['id'],
        'lastastrotime': device.get('lastastrotime'),
        'lasastroOP': device.get('lasastroOP')
    }
    response_json = json.dumps(data, ensure_ascii=False)
    return Response(response_json, content_type='application/json; charset=utf-8')

# Custom error handlers to ensure non-ASCII characters are handled
@app.errorhandler(400)
def bad_request(e: Exception) -> Response:
    response = {'error': str(e: Exception) -> Response}
    response_json = json.dumps(response, ensure_ascii=False)
    return Response(response_json, status=400, content_type='application/json; charset=utf-8')

@app.errorhandler(401)
def unauthorized(e: Exception) -> Response:
    response = {'error': 'Unauthorized access'}
    response_json = json.dumps(response, ensure_ascii=False)
    return Response(response_json, status=401, content_type='application/json; charset=utf-8')

@app.errorhandler(403)
def forbidden(e: Exception) -> Response:
    response = {'error': str(e: Exception) -> Response}
    response_json = json.dumps(response, ensure_ascii=False)
    return Response(response_json, status=403, content_type='application/json; charset=utf-8')

@app.errorhandler(404)
def resource_not_found(e: Exception) -> Response:
    response = {'error': str(e: Exception) -> Response}
    response_json = json.dumps(response, ensure_ascii=False)
    return Response(response_json, status=404, content_type='application/json; charset=utf-8')

@app.errorhandler(500)
def internal_server_error(e: Exception) -> Response:
    response = {'error': 'Internal server error'}
    response_json = json.dumps(response, ensure_ascii=False)
    return Response(response_json, status=500, content_type='application/json; charset=utf-8')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5053)
