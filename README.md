# 🏠 Home Assistant Skill

An skill for controlling smart home devices via [Home Assistant](https://www.home-assistant.io/) REST API.

## What It Does

- **Query** device states, entity information, and live context overview
- **Control** lights, switches, climate, media players, and more
- **List & filter** entities by type or availability
- **Call** any Home Assistant service and fire custom events
- **View** history, logbook, components, services, calendars, and error logs
- **Use** templates, camera snapshots, synthetic state helpers, and intent handling

## Environment Variables

| Variable | Description |
|----------|-------------|
| `HA_URL` | Home Assistant instance URL (e.g. `http://192.168.1.100:8123`) |
| `HA_TOKEN` | [Long-lived access token](https://www.home-assistant.io/docs/authentication/#your-account-profile) |

## Dependencies

```bash
# Install dependencies
pip install -r scripts/requirements.txt
```

## Key Commands

```bash
# Overview and discovery
python scripts/homeassistant_api.py check-api
python scripts/homeassistant_api.py get-config
python scripts/homeassistant_api.py get-components
python scripts/homeassistant_api.py get-services
python scripts/homeassistant_api.py get-events

# Entities
python scripts/homeassistant_api.py get-states
python scripts/homeassistant_api.py list-entities --domain light
python scripts/homeassistant_api.py get-entity light.living_room
python scripts/homeassistant_api.py set-state sensor.demo online --attributes '{"friendly_name": "Demo Sensor"}'
python scripts/homeassistant_api.py delete-entity sensor.demo

# Actions, events, and context
python scripts/homeassistant_api.py call-service light turn_on --entity-id light.living_room --data '{"brightness": 200}'
python scripts/homeassistant_api.py fire-event custom_action --data '{"source": "skill"}'
python scripts/homeassistant_api.py live-context

# History and templates
python scripts/homeassistant_api.py get-history light.living_room --timestamp 2026-03-24T00:00:00+00:00
python scripts/homeassistant_api.py get-logbook --entity light.living_room
python scripts/homeassistant_api.py render-template "{{ states('sun.sun') }}"

# Calendars and diagnostics
python scripts/homeassistant_api.py get-calendars
python scripts/homeassistant_api.py get-calendar-events calendar.family 2026-03-24T00:00:00+00:00 2026-03-31T00:00:00+00:00
python scripts/homeassistant_api.py check-config
python scripts/homeassistant_api.py get-error-log
```
