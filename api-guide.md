# API Command Documentation

The following commands demonstrate interacting with the `intrapi.py` API using `curl`. Replace placeholders like `your_server`, `your_id`, and `your_secret` with actual values for your setup.

---

## Authentication Headers
All API requests require authentication headers:
```bash
-H "CF-Access-Client-Id: your_id" \
-H "CF-Access-Client-Secret: your_secret"
```

---

## 1. Set Device to MANUAL Mode

```bash
curl -X POST -H "Content-Type: application/json" \
     -H "CF-Access-Client-Id: your_id" \
     -H "CF-Access-Client-Secret: your_secret" \
     -d '{"astroman": "MANUAL"}' \
     https://your_server/devices/{identifier}/astroman
```

Response:
```json
{"message": "Device {identifier} astroman set to MANUAL"}
```

---

## 2. Turn Device OFF

```bash
curl -X POST -H "Content-Type: application/json" \
     -H "CF-Access-Client-Id: your_id" \
     -H "CF-Access-Client-Secret: your_secret" \
     -d '{"state": "OFF"}' \
     https://your_server/devices/{identifier}/state
```

Response:
```json
{"message": "Device {identifier} turned OFF successfully"}
```

---

## 3. Turn Device ON

```bash
curl -X POST -H "Content-Type: application/json" \
     -H "CF-Access-Client-Id: your_id" \
     -H "CF-Access-Client-Secret: your_secret" \
     -d '{"state": "ON"}' \
     https://your_server/devices/{identifier}/state
```

Response:
```json
{"message": "Device {identifier} turned ON successfully"}
```

---

## 4. Set Device to ASTRO Mode

```bash
curl -X POST -H "Content-Type: application/json" \
     -H "CF-Access-Client-Id: your_id" \
     -H "CF-Access-Client-Secret: your_secret" \
     -d '{"astroman": "ASTRO"}' \
     https://your_server/devices/{identifier}/astroman
```

Response:
```json
{"message": "Device {identifier} astroman set to ASTRO"}
```

---

## Notes
- **Placeholders**: Replace `{identifier}` with the device's unique ID
- **Base URL**: Replace `your_server` with your server's base URL.
- **Authentication**: Replace `your_id` and `your_secret` with your API credentials.
- **Content-Type Header**: Ensure `Content-Type: application/json` is included for `POST` requests.
