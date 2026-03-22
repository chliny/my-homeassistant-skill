# 🏠 Home Assistant Skill

An skill for controlling smart home devices via [Home Assistant](https://www.home-assistant.io/) REST API.

## What It Does

- **Query** device states, entity information, and live context overview
- **Control** lights, switches, climate, media players, and more
- **List & filter** entities by type or availability
- **Call** any Home Assistant service
- **View** history, logbook, calendars, and error logs

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

## License

[MIT](LICENSE)