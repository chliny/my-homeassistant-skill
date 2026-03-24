---
name: homeassistant
description: Control smart home devices via Home Assistant REST API. Query device states, toggle lights/switches, adjust climate, and manage home automation.
metadata: {"openclaw": {"emoji":"🏠","requires":{"env":["HA_TOKEN", "HA_URL"], "bins": ["python"]}}}
---

# Home Assistant Skill

Interact with your Home Assistant instance via the official REST API.

### Available Methods

| Method | Description |
|--------|-------------|
| `check_api()` | Check if API is running |
| `get_config()` | Get HA configuration |
| `get_states()` | Get all entity states |
| `get_components()` | Get loaded Home Assistant components |
| `get_events()` | Get registered event types |
| `get_services()` | Get available services |
| `get_scenes()` | Get scene entities |
| `activate_scene(entity_id, transition)` | Activate a scene |
| `apply_scene(entities, transition)` | Apply an ad-hoc scene definition |
| `create_scene(scene_id, entities, snapshot_entities)` | Create a dynamic scene |
| `reload_scenes()` | Reload scenes |
| `get_automations()` | Get automation entities |
| `trigger_automation(entity_id, skip_condition, variables)` | Trigger an automation |
| `turn_on_automation(entity_id)` | Enable an automation |
| `turn_off_automation(entity_id, stop_actions)` | Disable an automation |
| `toggle_automation(entity_id)` | Toggle automation state |
| `reload_automations()` | Reload automations |
| `get_todo_lists()` | Get to-do list entities |
| `get_todo_items(entity_id, status)` | Get to-do items |
| `add_todo_item(entity_id, item, ...)` | Add a to-do item |
| `update_todo_item(entity_id, item, ...)` | Update a to-do item |
| `remove_todo_item(entity_id, item)` | Remove a to-do item |
| `remove_completed_todo_items(entity_id)` | Remove completed to-do items |
| `get_scripts()` | Get script entities |
| `run_script(entity_id, variables, return_response)` | Run a script |
| `turn_off_script(entity_id)` | Stop a running script |
| `toggle_script(entity_id)` | Toggle a script |
| `reload_scripts()` | Reload scripts |
| `get_input_booleans()` | Get input_boolean entities |
| `turn_on_input_boolean(entity_id)` | Turn on an input_boolean |
| `turn_off_input_boolean(entity_id)` | Turn off an input_boolean |
| `toggle_input_boolean(entity_id)` | Toggle an input_boolean |
| `reload_input_booleans()` | Reload input_booleans |
| `get_input_selects()` | Get input_select entities |
| `select_input_option(entity_id, option)` | Select an input_select option |
| `select_next_input_option(entity_id, cycle)` | Select next input_select option |
| `select_previous_input_option(entity_id, cycle)` | Select previous input_select option |
| `set_input_select_options(entity_id, options)` | Replace input_select options |
| `reload_input_selects()` | Reload input_selects |
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

# Show only light entities
python scripts/homeassistant_api.py list-available-entities --domain light
```

### Get entity state
```bash
# Get a specific entity
python scripts/homeassistant_api.py get-entity light.living_room

# Check if anyone is home
python scripts/homeassistant_api.py get-entity person.chliny
```

### Browse states, components, events, and services
```bash
# Dump all entity states as JSON
python scripts/homeassistant_api.py get-states


# Inspect loaded integrations/components
python scripts/homeassistant_api.py get-components

# List available event types
python scripts/homeassistant_api.py get-events

# List callable services
python scripts/homeassistant_api.py get-services
```

### Manage entity state representation
```bash
# Set a synthetic state in Home Assistant
python scripts/homeassistant_api.py set-state sensor.demo online --attributes '{"friendly_name": "Demo Sensor"}'
```

### Get live context (all entities overview)
```bash
python scripts/homeassistant_api.py live-context
```

### Work with scenes
```bash
# List scenes
python scripts/homeassistant_api.py get-scenes

# Activate a scene
python scripts/homeassistant_api.py activate-scene scene.movie_time --transition 2.5

# Apply a temporary scene definition
python scripts/homeassistant_api.py apply-scene --entities '{"light.living_room": {"state": "on", "brightness": 120}, "media_player.tv": "off"}'

# Create a dynamic scene from current entity state
python scripts/homeassistant_api.py create-scene before_window_open --snapshot-entities climate.ecobee light.ceiling_lights
```

### Work with automations
```bash
# List automations
python scripts/homeassistant_api.py get-automations

# Trigger an automation with variables
python scripts/homeassistant_api.py trigger-automation automation.good_night --variables '{"source": "cli"}'

# Disable an automation and stop active actions
python scripts/homeassistant_api.py turn-off-automation automation.good_night --stop-actions

# Re-enable or toggle an automation
python scripts/homeassistant_api.py turn-on-automation automation.good_night
python scripts/homeassistant_api.py toggle-automation automation.good_night
```

### Work with to-do lists
```bash
# List to-do lists
python scripts/homeassistant_api.py get-todo-lists

# Fetch incomplete items
python scripts/homeassistant_api.py get-todo-items todo.personal_tasks --status needs_action

# Add an item
python scripts/homeassistant_api.py add-todo-item todo.personal_tasks "Submit tax return" --due-date 2026-04-10 --description "Collect documents first"

# Mark an item completed
python scripts/homeassistant_api.py update-todo-item todo.personal_tasks "Submit tax return" --status completed

# Remove one item or clear completed ones
python scripts/homeassistant_api.py remove-todo-item todo.personal_tasks "Submit tax return"
python scripts/homeassistant_api.py clear-completed-todo todo.personal_tasks
```

### Work with scripts
```bash
# List scripts
python scripts/homeassistant_api.py get-scripts

# Run a script with variables
python scripts/homeassistant_api.py run-script script.good_morning --variables '{"room": "kitchen"}'

# Stop or toggle a script
python scripts/homeassistant_api.py turn-off-script script.good_morning
python scripts/homeassistant_api.py toggle-script script.good_morning
```

### Work with input booleans
```bash
# List input booleans
python scripts/homeassistant_api.py get-input-booleans

# Turn one on, off, or toggle it
python scripts/homeassistant_api.py turn-on-input-boolean input_boolean.guest_mode
python scripts/homeassistant_api.py turn-off-input-boolean input_boolean.guest_mode
python scripts/homeassistant_api.py toggle-input-boolean input_boolean.guest_mode
```

### Work with input selects
```bash
# List input selects
python scripts/homeassistant_api.py get-input-selects

# Select a specific option
python scripts/homeassistant_api.py select-input-option input_select.house_mode Away

# Step through options
python scripts/homeassistant_api.py select-next-input-option input_select.house_mode
python scripts/homeassistant_api.py select-previous-input-option input_select.house_mode --no-cycle

# Replace the available options
python scripts/homeassistant_api.py set-input-select-options input_select.house_mode Home Away Night Vacation
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

# Return data from services that support it
python scripts/homeassistant_api.py call-service weather get_forecasts --entity-id weather.home --data '{"type": "daily"}' --return-response
```

### Fire events
```bash
python scripts/homeassistant_api.py fire-event custom_action --data '{"source": "skill", "action": "run"}'
```

### Query history and logbook
```bash
# Get history for one or more entities
python scripts/homeassistant_api.py get-history light.living_room sensor.temperature --timestamp 2026-03-24T00:00:00+00:00 --end-time 2026-03-24T23:59:59+00:00

# Get entity logbook entries
python scripts/homeassistant_api.py get-logbook --entity light.living_room --timestamp 2026-03-24T00:00:00+00:00 --end-time 2026-03-24T23:59:59+00:00
```

### Render templates
```bash
# Render inline
python scripts/homeassistant_api.py render-template "{{ states('sun.sun') }}"

# Render from a file
python scripts/homeassistant_api.py render-template --file template.j2
```

### Calendars
```bash
# List calendar entities
python scripts/homeassistant_api.py get-calendars

# Fetch events for a calendar
python scripts/homeassistant_api.py get-calendar-events calendar.family 2026-03-24T00:00:00+00:00 2026-03-31T00:00:00+00:00
```

### Camera and intent helpers
```bash
# Save a camera snapshot
python scripts/homeassistant_api.py get-camera-image camera.front_door --output front-door.jpg

# Handle an intent
python scripts/homeassistant_api.py handle-intent HassTurnOn --data '{"name": "Living room light", "area": "Living Room"}'
```

### Get configuration
```bash
python scripts/homeassistant_api.py get-config
```

### Diagnostics helpers
```bash
# Validate Home Assistant configuration
python scripts/homeassistant_api.py check-config

# Fetch Home Assistant error log
python scripts/homeassistant_api.py get-error-log
```

## Important Notes
- Unavailable entities should not be controlled. Therefore, for operation commands, prefer using the `list-available-entities` command when looking up entities
- For turning lights on or off, prioritize operating the light's switch rather than controlling the light directly
- For light-related commands, **ignore all indicator light entities**
- If a light's switch is on, consider the light as on; conversely, if the switch is off, the light must be off
- If a device is offline, **do not assume it is on**

## Dependencies

- Python 3.10+
- `aiohttp` library

Install dependencies:
```bash
pip install -r scripts/requirements.txt
```
