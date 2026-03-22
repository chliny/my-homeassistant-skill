---
name: homeassistant
description: Control smart home devices via Home Assistant REST API. Query device states, toggle lights/switches, adjust climate, and manage home automation.
metadata: {"openclaw": {"emoji":"🏠","requires":{"env":["HA_TOKEN", "HA_URL"], "bins": ["python", "pip"]}}}  
---

# Home Assistant Skill

Interact with your Home Assistant instance via the official REST API.

### Available Methods

| Method | Description |
|--------|-------------|
| `check_api()` | Check if API is running |
| `get_config()` | Get HA configuration |
| `get_states()` | Get all entity states |
| `get_entity(entity_id)` | Get specific entity state |
| `set_state(entity_id, state, attributes)` | Update entity state |
| `list_entities()` | List all entities with ID, state and friendly name |
| `get_live_context()` | Get formatted entity overview |
| `call_service(domain, service, entity_id, **kwargs)` | Call a service |
| `fire_event(event_type, event_data)` | Fire an event |
| `get_history(entity_ids, ...)` | Get state history |
| `get_logbook(timestamp, entity, end_time)` | Get logbook entries |
| `render_template(template)` | Render HA template |
| `get_camera_image(entity_id, timestamp)` | Get camera image |
| `get_calendars()` | Get calendar entities |
| `get_calendar_events(entity_id, start, end)` | Get calendar events |
| `get_error_log()` | Get error log |
| `check_config()` | Check configuration |
| `handle_intent(name, data)` | Handle intent |


## Examples

### Check API status
```bash
python scripts/homeassistant_api.py check-api
```

### List all entities
```bash
python scripts/homeassistant_api.py list-entities
```
Or list only available entities:
```bash
python scripts/homeassistant_api.py list-available-entities
```

Output format: `entity_id state friendly_name`
```
light.living_room on Living Room Light
switch.kitchen off Kitchen Switch
sensor.temperature 23.5 Temperature Sensor
```

### Find Entities
```bash
# Find light-related entities
python scripts/homeassistant_api.py list-available-entities | grep light

# Find switch-related entities
python scripts/homeassistant_api.py list-available-entities | grep switch
```

### Get entity state
```bash
# Get a specific entity
python scripts/homeassistant_api.py get-entity light.living_room

# Check if anyone is home
python scripts/homeassistant_api.py get-entity person.chliny
```

### Get live context (all entities overview)
```bash
python scripts/homeassistant_api.py live-context
```

### Call services
```bash
# Turn on a light
python scripts/homeassistant_api.py call-service light turn_on --entity-id light.living_room

# Turn off a light
python scripts/homeassistant_api.py call-service light turn_off --entity-id light.living_room

# Set light brightness
python scripts/homeassistant_api.py call-service light turn_on --entity-id light.living_room --data '{"brightness": 200}'

# Set light color
python scripts/homeassistant_api.py call-service light turn_on --entity-id light.living_room --data '{"rgb_color": [255, 0, 0]}'

# Toggle a switch
python scripts/homeassistant_api.py call-service switch toggle --entity-id switch.living_room

# Control media player
python scripts/homeassistant_api.py call-service media_player play_pause --entity-id media_player.living_room

# Set climate temperature
python scripts/homeassistant_api.py call-service climate set_temperature --entity-id climate.living_room --data '{"temperature": 22}'
```

### Get configuration
```bash
python scripts/homeassistant_api.py get-config
```

## Important Notes
- Unavailable entities should not be controlled. Therefore, for operation commands, prefer using the `list-available-entities` command when looking up entities
- For turning lights on or off, prioritize operating the light's switch rather than controlling the light directly
- For light-related commands, **ignore all indicator light entities**
- If a light's switch is on, consider the light as on; conversely, if the switch is off, the light must be off
- If a device is offline, **do not assume it is on**

## Dependencies

- Python 3.10+
- `requests` library

Install dependencies:
```bash
pip install -r scripts/requirements.txt
```
