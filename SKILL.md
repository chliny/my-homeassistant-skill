---
name: homeassistant
description: Interact with Home Assistant via REST API. Supports getting device states, calling services, listing entities, and querying home status. Use when working with Home Assistant smart home systems, checking device states, or controlling home automation.
---

# Home Assistant Skill

Interact with your Home Assistant instance via the official REST API.

## Configuration

Get environment variables from the following locations. **Note: Load only once, and only `HA_URL` and `HA_TOKEN` are required**
```
~/.openclaw/.env
.env
~/.env
```

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

### 查找实体
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

## Additional Notes
- Unavailable entities should not be controlled. Therefore, for operation commands, prefer using the `list-available-entities` command when looking up entities

## Dependencies

- Python 3.10+
- `requests` library

Install dependencies:
```bash
pip install -r scripts/requirements.txt
```
