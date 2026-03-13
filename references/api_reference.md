# Home Assistant REST API Reference

> Source: https://developers.home-assistant.io/docs/api/rest  
> Last Updated: Feb 2, 2026

## Table of Contents

1. [General Information](#general-information)
2. [Authentication](#authentication)
3. [API Endpoints](#api-endpoints)
   - [System Status](#system-status)
   - [Entity States](#entity-states)
   - [Services](#services)
   - [Events](#events)
   - [History](#history)
   - [Logbook](#logbook)
   - [Template](#template)
   - [Camera](#camera)
   - [Calendar](#calendar)
   - [Configuration](#configuration)
   - [Intent](#intent)
4. [HTTP Status Codes](#http-status-codes)
5. [Usage Examples](#usage-examples)

---

## General Information

- **Base URL**: `http://IP_ADDRESS:8123/api/`
- **Default Port**: `8123`
- **Data Format**: JSON (except `/api/error_log` returns plain text, `/api/camera_proxy/<entity_id>` returns image data)

## Authentication

All API calls require the following header:

```
Authorization: Bearer TOKEN
Content-Type: application/json
```

**Token**: Long-lived access token, obtainable from the frontend profile page (`http://IP_ADDRESS:8123/profile`).

**Note**: If not using the frontend, add `api:` integration to `configuration.yaml`.

---

## API Endpoints

### System Status

#### Check API Status

```http
GET /api/
```

Check if API is running. **Note**: URL must include trailing slash.

**Response**:
```json
{
  "message": "API running."
}
```

---

#### Get Configuration

```http
GET /api/config
```

Get current configuration information.

**Response**:
```json
{
  "components": ["homeassistant", "api", ...],
  "config_dir": "/config",
  "elevation": 0,
  "latitude": 37.7749,
  "longitude": -122.4194,
  "unit_system": {
    "length": "km",
    "mass": "g",
    "temperature": "°C",
    "volume": "L"
  },
  "version": "2024.1.0",
  "time_zone": "America/Los_Angeles"
}
```

---

#### Get Components

```http
GET /api/components
```

Get list of loaded components.

**Response**:
```json
["homeassistant", "api", "automation", "script", ...]
```

---

#### Get Error Log

```http
GET /api/error_log
```

Retrieve all errors logged during the current session.

**Response**: Plain text error log content.

---

### Entity States

#### Get All States

```http
GET /api/states
```

Get all entity states.

**Response**:
```json
[
  {
    "entity_id": "light.living_room",
    "state": "on",
    "attributes": {
      "friendly_name": "Living Room Light",
      "brightness": 255
    },
    "last_changed": "2024-01-01T12:00:00+00:00",
    "last_updated": "2024-01-01T12:00:00+00:00"
  }
]
```

---

#### Get Entity State

```http
GET /api/states/<entity_id>
```

Get state of a specific entity.

**Path Parameters**:
- `entity_id` (required): Entity ID (e.g., `light.living_room`)

**Response**:
```json
{
  "entity_id": "light.living_room",
  "state": "on",
  "attributes": {
    "friendly_name": "Living Room Light",
    "brightness": 255
  },
  "last_changed": "2024-01-01T12:00:00+00:00"
}
```

**Error**: Returns 404 if entity not found.

---

#### Set Entity State

```http
POST /api/states/<entity_id>
```

Update or create an entity state.

**Path Parameters**:
- `entity_id` (required): Entity ID

**Request Body**:
```json
{
  "state": "on",
  "attributes": {
    "friendly_name": "Living Room Light",
    "brightness": 200
  }
}
```

**Response**: Updated state object.

**Warning**: This only updates the state representation in Home Assistant, it does NOT communicate with the actual device. To control devices, use the Services API.

---

#### Delete Entity

```http
DELETE /api/states/<entity_id>
```

Delete an entity.

**Path Parameters**:
- `entity_id` (required): Entity ID

**Response**: Empty on success.

---

### Services

#### Get Services

```http
GET /api/services
```

Get list of available services.

**Response**:
```json
[
  {
    "domain": "light",
    "services": {
      "turn_on": {...},
      "turn_off": {...},
      "toggle": {...}
    }
  }
]
```

---

#### Call Service

```http
POST /api/services/<domain>/<service>
```

Call a service within a domain.

**Path Parameters**:
- `domain` (required): Service domain (e.g., `light`, `switch`)
- `service` (required): Service name (e.g., `turn_on`, `turn_off`)

**Query Parameters**:
- `return_response` (optional): Include to get response data from services that support it

**Request Body** (optional):
```json
{
  "entity_id": "light.living_room",
  "brightness": 200,
  "rgb_color": [255, 0, 0]
}
```

**Response**: Array of changed entity states during execution, or object with `changed_states` and `service_response` if `return_response` is set.

**Note**: If the service supports returning data (e.g., weather forecast), you MUST include `?return_response` or you'll get a 400 error.

---

### Events

#### Get Events

```http
GET /api/events
```

Get list of events.

**Response**:
```json
[
  {
    "event": "homeassistant_start",
    "listener_count": 5
  }
]
```

---

#### Fire Event

```http
POST /api/events/<event_type>
```

Fire an event.

**Path Parameters**:
- `event_type` (required): Event type name

**Request Body** (optional):
```json
{
  "custom_data": "value"
}
```

**Response**:
```json
{
  "message": "Event <event_type> fired."
}
```

---

### History

#### Get State History

```http
GET /api/history/period/<timestamp>
```

Get state history for entities.

**Path Parameters**:
- `timestamp` (optional): Start timestamp (defaults to 1 day ago)

**Query Parameters**:
- `filter_entity_id` (required): Comma-separated list of entity IDs
- `end_time` (optional): End timestamp
- `minimal_response` (optional): Only return last changed and state
- `no_attributes` (optional): Skip attributes to reduce response size
- `significant_changes_only` (optional): Only return significant changes

**Response**:
```json
[
  [
    {
      "entity_id": "light.living_room",
      "state": "on",
      "last_changed": "2024-01-01T10:00:00+00:00"
    }
  ]
]
```

---

### Logbook

#### Get Logbook Entries

```http
GET /api/logbook/<timestamp>
```

Get logbook entries.

**Path Parameters**:
- `timestamp` (optional): Start timestamp (defaults to 1 day ago)

**Query Parameters**:
- `entity` (optional): Filter by entity ID
- `end_time` (optional): End timestamp

**Response**:
```json
[
  {
    "entity_id": "light.living_room",
    "message": "turned on",
    "when": "2024-01-01T10:00:00+00:00",
    "domain": "light"
  }
]
```

---

### Template

#### Render Template

```http
POST /api/template
```

Render a Home Assistant Jinja2 template.

**Request Body**:
```json
{
  "template": "The temperature is {{ states('sensor.temperature') }}°C"
}
```

**Response**: Plain text (rendered result).

---

### Camera

#### Get Camera Image

```http
GET /api/camera_proxy/<camera entity_id>
```

Get image from a camera.

**Path Parameters**:
- `camera entity_id` (required): Camera entity ID

**Query Parameters**:
- `time` (optional): Timestamp for historical image

**Response**: Binary image data (e.g., JPEG).

---

### Calendar

#### Get Calendars

```http
GET /api/calendars
```

Get list of calendar entities.

**Response**:
```json
[
  {
    "entity_id": "calendar.personal",
    "name": "Personal Calendar"
  }
]
```

---

#### Get Calendar Events

```http
GET /api/calendars/<calendar entity_id>
```

Get events from a calendar within a time range.

**Path Parameters**:
- `calendar entity_id` (required): Calendar entity ID

**Query Parameters**:
- `start` (required): Start timestamp
- `end` (required): End timestamp

**Response**:
```json
[
  {
    "summary": "Meeting",
    "start": "2024-01-01T10:00:00",
    "end": "2024-01-01T11:00:00",
    "description": "Team meeting"
  }
]
```

---

### Configuration

#### Check Configuration

```http
POST /api/config/core/check_config
```

Trigger a check of `configuration.yaml`. Requires `config` integration.

**Response**:
```json
{
  "result": "valid",
  "errors": null
}
```

---

### Intent

#### Handle Intent

```http
POST /api/intent/handle
```

Handle an intent. Requires `intent:` in `configuration.yaml`.

**Request Body**:
```json
{
  "name": "TurnOn",
  "data": {
    "entity_id": "light.living_room"
  }
}
```

**Response**: Intent processing result.

---

## HTTP Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request |
| 401 | Unauthorized |
| 404 | Not Found |
| 405 | Method Not Allowed |

---

## Usage Examples

### cURL Examples

```bash
# Get configuration
curl \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  http://localhost:8123/api/config

# Get entity state
curl \
  -H "Authorization: Bearer TOKEN" \
  http://localhost:8123/api/states/light.living_room

# Call service
curl -X POST \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"entity_id": "light.study_light"}' \
  http://localhost:8123/api/services/light/turn_on

# Render template
curl -X POST \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"template": "Temperature: {{ states(\"sensor.temperature\") }}"}' \
  http://localhost:8123/api/template
```

### Python Examples

```python
import requests

BASE_URL = "http://localhost:8123/api"
HEADERS = {
    "Authorization": "Bearer TOKEN",
    "Content-Type": "application/json"
}

# Get all states
response = requests.get(f"{BASE_URL}/states", headers=HEADERS)
states = response.json()

# Call service
response = requests.post(
    f"{BASE_URL}/services/light/turn_on",
    headers=HEADERS,
    json={"entity_id": "light.study_light"}
)

# Get history
response = requests.get(
    f"{BASE_URL}/history/period/2024-01-01T00:00:00Z",
    headers=HEADERS,
    params={"filter_entity_id": "light.living_room"}
)
```

---

## Key Notes

1. **State vs Service**: `POST /api/states/<entity_id>` only updates HA's internal state representation. To control actual devices, use `POST /api/services/<domain>/<service>`.

2. **Service Response**: If a service supports returning data, you MUST include `?return_response` query parameter.

3. **History Optimization**: Use `minimal_response` and `no_attributes` parameters to reduce response size.

4. **Authentication**: Always include the `Authorization: Bearer TOKEN` header.
