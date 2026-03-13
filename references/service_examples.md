# Home Assistant Service Call Examples

This document provides comprehensive examples for common Home Assistant service calls.

## Table of Contents

1. [Light Control](#light-control)
2. [Switch Control](#switch-control)
3. [Climate Control](#climate-control)
4. [Media Player Control](#media-player-control)
5. [Cover/Blind Control](#coverblind-control)
6. [Fan Control](#fan-control)
7. [Scripts & Automations](#scripts--automations)
8. [Notifications](#notifications)
9. [Scene Activation](#scene-activation)
10. [Device-Specific Examples](#device-specific-examples)

---

## Light Control

### Basic Operations

```python
# Turn on light
ha.call_service("light", "turn_on", entity_id="light.living_room")

# Turn off light
ha.call_service("light", "turn_off", entity_id="light.living_room")

# Toggle light
ha.call_service("light", "toggle", entity_id="light.living_room")
```

### Brightness Control

```python
# Set brightness (0-255)
ha.call_service("light", "turn_on", 
    entity_id="light.living_room",
    brightness=200
)

# Set brightness percentage (0-100)
ha.call_service("light", "turn_on",
    entity_id="light.living_room",
    brightness_pct=75
)
```

### Color Control

```python
# RGB color (0-255 each)
ha.call_service("light", "turn_on",
    entity_id="light.living_room",
    rgb_color=[255, 0, 0]  # Red
)

# Color temperature (mireds)
ha.call_service("light", "turn_on",
    entity_id="light.living_room",
    color_temp=300
)

# Color temperature (Kelvin)
ha.call_service("light", "turn_on",
    entity_id="light.living_room",
    kelvin=4000
)

# XY color
ha.call_service("light", "turn_on",
    entity_id="light.living_room",
    xy_color=[0.3, 0.5]
)

# HS color (hue 0-360, saturation 0-100)
ha.call_service("light", "turn_on",
    entity_id="light.living_room",
    hs_color=[240, 100]  # Blue
)
```

### Effects

```python
# Set effect
ha.call_service("light", "turn_on",
    entity_id="light.living_room",
    effect="colorloop"
)

# Flash effect
ha.call_service("light", "turn_on",
    entity_id="light.living_room",
    flash="short"  # or "long"
)
```

### Transition

```python
# Fade in over 5 seconds
ha.call_service("light", "turn_on",
    entity_id="light.living_room",
    brightness=255,
    transition=5
)

# Fade out over 3 seconds
ha.call_service("light", "turn_off",
    entity_id="light.living_room",
    transition=3
)
```

### Multiple Lights

```python
# Control multiple lights at once
ha.call_service("light", "turn_on",
    entity_id="light.living_room,light.kitchen,light.bedroom",
    brightness=200
)

# All lights in a group
ha.call_service("light", "turn_on",
    entity_id="group.all_lights",
    brightness_pct=100
)
```

---

## Switch Control

```python
# Turn on
ha.call_service("switch", "turn_on", entity_id="switch.kitchen_outlet")

# Turn off
ha.call_service("switch", "turn_off", entity_id="switch.kitchen_outlet")

# Toggle
ha.call_service("switch", "toggle", entity_id="switch.kitchen_outlet")
```

---

## Climate Control

### Temperature

```python
# Set temperature
ha.call_service("climate", "set_temperature",
    entity_id="climate.living_room",
    temperature=22
)

# Set temperature with HVAC mode
ha.call_service("climate", "set_temperature",
    entity_id="climate.living_room",
    temperature=22,
    hvac_mode="heat"
)

# Set high/low temperature (for auto mode)
ha.call_service("climate", "set_temperature",
    entity_id="climate.living_room",
    target_temp_high=25,
    target_temp_low=20
)
```

### HVAC Mode

```python
# Set HVAC mode
ha.call_service("climate", "set_hvac_mode",
    entity_id="climate.living_room",
    hvac_mode="heat"  # off, heat, cool, auto, dry, fan_only
)
```

### Preset Mode

```python
# Set preset mode
ha.call_service("climate", "set_preset_mode",
    entity_id="climate.living_room",
    preset_mode="away"  # home, away, sleep, etc.
)
```

### Fan Mode

```python
# Set fan mode
ha.call_service("climate", "set_fan_mode",
    entity_id="climate.living_room",
    fan_mode="auto"  # on, off, auto, low, medium, high
)
```

### Swing Mode

```python
# Set swing mode
ha.call_service("climate", "set_swing_mode",
    entity_id="climate.living_room",
    swing_mode="horizontal"  # off, horizontal, vertical, both
)
```

---

## Media Player Control

### Basic Playback

```python
# Play/Pause
ha.call_service("media_player", "play_pause", entity_id="media_player.living_room")

# Play
ha.call_service("media_player", "media_play", entity_id="media_player.living_room")

# Pause
ha.call_service("media_player", "media_pause", entity_id="media_player.living_room")

# Stop
ha.call_service("media_player", "media_stop", entity_id="media_player.living_room")

# Next track
ha.call_service("media_player", "media_next_track", entity_id="media_player.living_room")

# Previous track
ha.call_service("media_player", "media_previous_track", entity_id="media_player.living_room")
```

### Volume Control

```python
# Set volume (0.0 - 1.0)
ha.call_service("media_player", "volume_set",
    entity_id="media_player.living_room",
    volume_level=0.5
)

# Volume up
ha.call_service("media_player", "volume_up", entity_id="media_player.living_room")

# Volume down
ha.call_service("media_player", "volume_down", entity_id="media_player.living_room")

# Mute
ha.call_service("media_player", "volume_mute",
    entity_id="media_player.living_room",
    is_volume_muted=True
)
```

### Media Selection

```python
# Play media
ha.call_service("media_player", "play_media",
    entity_id="media_player.living_room",
    media_content_id="http://example.com/song.mp3",
    media_content_type="music"
)

# Select source
ha.call_service("media_player", "select_source",
    entity_id="media_player.living_room",
    source="TV"
)
```

---

## Cover/Blind Control

```python
# Open cover
ha.call_service("cover", "open_cover", entity_id="cover.living_room_blinds")

# Close cover
ha.call_service("cover", "close_cover", entity_id="cover.living_room_blinds")

# Stop cover
ha.call_service("cover", "stop_cover", entity_id="cover.living_room_blinds")

# Set position (0-100, 0=closed, 100=open)
ha.call_service("cover", "set_cover_position",
    entity_id="cover.living_room_blinds",
    position=50
)

# Toggle
ha.call_service("cover", "toggle", entity_id="cover.living_room_blinds")
```

---

## Fan Control

```python
# Turn on
ha.call_service("fan", "turn_on", entity_id="fan.living_room")

# Turn off
ha.call_service("fan", "turn_off", entity_id="fan.living_room")

# Toggle
ha.call_service("fan", "toggle", entity_id="fan.living_room")

# Set speed
ha.call_service("fan", "set_speed",
    entity_id="fan.living_room",
    speed="high"  # low, medium, high
)

# Set percentage speed
ha.call_service("fan", "set_percentage",
    entity_id="fan.living_room",
    percentage=75
)

# Set preset mode
ha.call_service("fan", "set_preset_mode",
    entity_id="fan.living_room",
    preset_mode="breeze"
)

# Set direction
ha.call_service("fan", "set_direction",
    entity_id="fan.living_room",
    direction="reverse"
)
```

---

## Scripts & Automations

### Scripts

```python
# Turn on script
ha.call_service("script", "turn_on", entity_id="script.morning_routine")

# Turn off script
ha.call_service("script", "turn_off", entity_id="script.morning_routine")

# Toggle script
ha.call_service("script", "toggle", entity_id="script.morning_routine")

# Reload scripts
ha.call_service("script", "reload")
```

### Automations

```python
# Turn on automation
ha.call_service("automation", "turn_on", entity_id="automation.lights_on_sunset")

# Turn off automation
ha.call_service("automation", "turn_off", entity_id="automation.lights_on_sunset")

# Toggle automation
ha.call_service("automation", "toggle", entity_id="automation.lights_on_sunset")

# Trigger automation
ha.call_service("automation", "trigger", entity_id="automation.lights_on_sunset")

# Reload automations
ha.call_service("automation", "reload")
```

---

## Notifications

### Persistent Notification

```python
ha.call_service("persistent_notification", "create",
    title="System Alert",
    message="Something important happened!",
    notification_id="alert_001"
)

# Dismiss notification
ha.call_service("persistent_notification", "dismiss",
    notification_id="alert_001"
)
```

### Mobile App Notification

```python
ha.call_service("notify", "mobile_app_iphone",
    title="Alert",
    message="Motion detected in the living room",
    data={
        "push": {
            "sound": "default"
        },
        "attachment": {
            "url": "/api/camera_proxy/camera.living_room"
        }
    }
)
```

---

## Scene Activation

```python
# Activate scene
ha.call_service("scene", "turn_on", entity_id="scene.movie_night")

# Apply scene with transition
ha.call_service("scene", "turn_on",
    entity_id="scene.movie_night",
    transition=10
)
```

---

## Device-Specific Examples

### Vacuum

```python
# Start cleaning
ha.call_service("vacuum", "start", entity_id="vacuum.roomba")

# Stop
ha.call_service("vacuum", "stop", entity_id="vacuum.roomba")

# Return to dock
ha.call_service("vacuum", "return_to_base", entity_id="vacuum.roomba")

# Clean specific room
ha.call_service("vacuum", "send_command",
    entity_id="vacuum.roomba",
    command="app_segment_clean",
    params=[18, 20]  # Room IDs
)
```

### Lock

```python
# Lock
ha.call_service("lock", "lock", entity_id="lock.front_door")

# Unlock
ha.call_service("lock", "unlock", entity_id="lock.front_door")

# Open (for supported locks)
ha.call_service("lock", "open", entity_id="lock.front_door")
```

### Garage Door

```python
# Open
ha.call_service("cover", "open_cover", entity_id="cover.garage_door")

# Close
ha.call_service("cover", "close_cover", entity_id="cover.garage_door")
```

### Water Heater

```python
# Turn on
ha.call_service("water_heater", "turn_on", entity_id="water_heater.water_heater")

# Set temperature
ha.call_service("water_heater", "set_temperature",
    entity_id="water_heater.water_heater",
    temperature=55
)

# Set operation mode
ha.call_service("water_heater", "set_operation_mode",
    entity_id="water_heater.water_heater",
    operation_mode="eco"  # off, eco, electric, gas, heat_pump, performance
)
```

### Humidifier

```python
# Turn on
ha.call_service("humidifier", "turn_on", entity_id="humidifier.living_room")

# Set humidity
ha.call_service("humidifier", "set_humidity",
    entity_id="humidifier.living_room",
    humidity=50
)

# Set mode
ha.call_service("humidifier", "set_mode",
    entity_id="humidifier.living_room",
    mode="auto"
)
```

---

## Using CLI

```bash
# Turn on light
python scripts/homeassistant_api.py call-service light turn_on --entity-id light.living_room

# Turn on light with brightness
python scripts/homeassistant_api.py call-service light turn_on --entity-id light.living_room --data '{"brightness": 200}'

# Set light color
python scripts/homeassistant_api.py call-service light turn_on --entity-id light.living_room --data '{"rgb_color": [255, 0, 0]}'

# Set climate temperature
python scripts/homeassistant_api.py call-service climate set_temperature --entity-id climate.living_room --data '{"temperature": 22}'

# Control media player
python scripts/homeassistant_api.py call-service media_player play_pause --entity-id media_player.living_room
```

---

## Tips

1. **Multiple Entities**: Use comma-separated list: `"light.living_room,light.kitchen"`

2. **All Entities in Domain**: Use `"all"` as entity_id: `entity_id="all"` (for lights, fans, etc.)

3. **Groups**: Reference groups: `entity_id="group.living_room_lights"`

4. **Area-Based**: Control all entities in an area: `area_id="living_room"`

5. **Template in Service Data**: You can use templates in service data fields when calling through HA's service system.
