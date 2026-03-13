# Home Assistant REST API Quick Reference

## Authentication

```bash
Authorization: Bearer <LONG_LIVED_TOKEN>
Content-Type: application/json
```

## Endpoints Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| **System** |||
| GET | `/api/` | Check API status |
| GET | `/api/config` | Get configuration |
| GET | `/api/components` | Get loaded components |
| GET | `/api/error_log` | Get error log (plain text) |
| **Entities** |||
| GET | `/api/states` | Get all entity states |
| GET | `/api/states/<entity_id>` | Get specific entity |
| POST | `/api/states/<entity_id>` | Update/create state |
| DELETE | `/api/states/<entity_id>` | Delete entity |
| **Services** |||
| GET | `/api/services` | List available services |
| POST | `/api/services/<domain>/<service>` | Call service |
| **Events** |||
| GET | `/api/events` | List events |
| POST | `/api/events/<event_type>` | Fire event |
| **History** |||
| GET | `/api/history/period/<timestamp>` | Get state history |
| GET | `/api/logbook/<timestamp>` | Get logbook entries |
| **Media** |||
| GET | `/api/camera_proxy/<entity_id>` | Get camera image (binary) |
| **Calendar** |||
| GET | `/api/calendars` | List calendars |
| GET | `/api/calendars/<entity_id>` | Get calendar events |
| **Config** |||
| POST | `/api/template` | Render Jinja2 template |
| POST | `/api/config/core/check_config` | Check configuration |
| POST | `/api/intent/handle` | Handle intent |

## Common Service Calls

### Lights

```bash
# Turn on
POST /api/services/light/turn_on
{"entity_id": "light.living_room"}

# Turn on with brightness
POST /api/services/light/turn_on
{"entity_id": "light.living_room", "brightness": 200}

# Turn on with color
POST /api/services/light/turn_on
{"entity_id": "light.living_room", "rgb_color": [255, 0, 0]}

# Turn off
POST /api/services/light/turn_off
{"entity_id": "light.living_room"}

# Toggle
POST /api/services/light/toggle
{"entity_id": "light.living_room"}
```

### Switches

```bash
POST /api/services/switch/turn_on
{"entity_id": "switch.kitchen"}

POST /api/services/switch/turn_off
{"entity_id": "switch.kitchen"}

POST /api/services/switch/toggle
{"entity_id": "switch.kitchen"}
```

### Climate

```bash
# Set temperature
POST /api/services/climate/set_temperature
{"entity_id": "climate.living_room", "temperature": 22}

# Set HVAC mode
POST /api/services/climate/set_hvac_mode
{"entity_id": "climate.living_room", "hvac_mode": "heat"}
```

### Media Player

```bash
POST /api/services/media_player/play_pause
{"entity_id": "media_player.living_room"}

POST /api/services/media_player/volume_set
{"entity_id": "media_player.living_room", "volume_level": 0.5}
```

### Scripts & Automations

```bash
# Trigger script
POST /api/services/script/turn_on
{"entity_id": "script.morning_routine"}

# Trigger automation
POST /api/services/automation/trigger
{"entity_id": "automation.lights_on_sunset"}
```

## Common Query Parameters

### History (`/api/history/period/<timestamp>`)

| Parameter | Description |
|-----------|-------------|
| `filter_entity_id` | Comma-separated entity IDs (required) |
| `end_time` | End timestamp |
| `minimal_response` | Only return last changed and state |
| `no_attributes` | Skip attributes |
| `significant_changes_only` | Only significant changes |

### Services (`/api/services/<domain>/<service>`)

| Parameter | Description |
|-----------|-------------|
| `return_response` | Get response data from service |

## Response Formats

### Entity State Object

```json
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
```

### Service Response

```json
[
  {
    "entity_id": "light.living_room",
    "state": "on",
    "attributes": {...}
  }
]
```

### History Response

```json
[
  [
    {
      "entity_id": "light.living_room",
      "state": "off",
      "last_changed": "2024-01-01T08:00:00+00:00"
    },
    {
      "entity_id": "light.living_room",
      "state": "on",
      "last_changed": "2024-01-01T10:00:00+00:00"
    }
  ]
]
```

## Python Implementation Reference

The Python client (`scripts/homeassistant_api.py`) provides:

```python
from homeassistant_api import HomeAssistantAPI

# Initialize (uses HA_URL and HA_TOKEN from environment)
with HomeAssistantAPI() as ha:
    # System
    ha.check_api()
    ha.get_config()
    
    # Entities
    ha.get_states()
    ha.get_entity("light.living_room")
    ha.set_state("sensor.custom", "value", {"unit": "°C"})
    ha.list_entities()  # Returns "entity_id state friendly_name"
    
    # Services
    ha.call_service("light", "turn_on", entity_id="light.living_room")
    ha.call_service("light", "turn_on", entity_id="light.living_room", brightness=200)
    
    # Events
    ha.fire_event("custom_event", {"data": "value"})
    
    # History
    ha.get_history(["light.living_room"], timestamp="2024-01-01T00:00:00Z")
    ha.get_logbook()
    
    # Template
    ha.render_template("{{ states('sensor.temperature') }}")
    
    # Camera
    image_data = ha.get_camera_image("camera.front_door")
    
    # Calendar
    ha.get_calendars()
    ha.get_calendar_events("calendar.personal", start, end)
```

## Error Handling

| HTTP Code | Meaning | Action |
|-----------|---------|--------|
| 200 | Success | Process response |
| 400 | Bad Request | Check request body/params |
| 401 | Unauthorized | Check token |
| 404 | Not Found | Check entity_id/path |
| 405 | Method Not Allowed | Check HTTP method |

## Important Notes

1. **State vs Service**: `POST /api/states/<entity_id>` does NOT control devices. Use `POST /api/services/<domain>/<service>` to control devices.

2. **Return Response**: Services that return data require `?return_response` query parameter.

3. **Internal Network Detection**: The Python client auto-detects internal URLs and disables proxy for them.

4. **SSL Verification**: Set `verify_ssl=False` in constructor for self-signed certificates.
