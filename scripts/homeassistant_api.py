#!/usr/bin/env python3
"""
Home Assistant REST API Client

Python client library for Home Assistant RESTful API.
HA_URL and HA_TOKEN are retrieved from environment variables.
"""

import os
import json
import ipaddress
import socket
import sys
import urllib3
from typing import Any
from urllib.parse import urlparse
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Disable insecure request warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class HomeAssistantAPI:
    """Home Assistant REST API client"""

    def __init__(
        self,
        url: str | None = None,
        token: str | None = None,
        timeout: int = 10,
        verify_ssl: bool = False,
    ):
        """
        Initialize Home Assistant API client

        Args:
            url: Home Assistant URL, defaults to HA_URL environment variable
            token: Long-lived access token, defaults to HA_TOKEN environment variable
            timeout: Request timeout in seconds
            verify_ssl: Whether to verify SSL certificate
        """
        self.url: str = (url or os.environ.get("HA_URL", "")).rstrip("/")
        self.token: str = token or os.environ.get("HA_TOKEN", "")

        if not self.url:
            raise ValueError(
                "HA_URL not set, please set environment variable or pass url parameter"
            )
        if not self.token:
            raise ValueError(
                "HA_TOKEN not set, please set environment variable or pass token parameter"
            )

        self.timeout: int = timeout
        self.verify_ssl: bool = verify_ssl

        # Check if URL points to internal network
        if self._check_internal_url():
            self._unset_proxies()

        # Configure session and retry strategy
        self.session: requests.Session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Set default request headers
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        self.session.headers.update(self.headers)

    def _is_private_ip(self, ip: str) -> bool:
        """
        Check if IP address is private/internal

        Args:
            ip: IP address string

        Returns:
            True if private/internal IP
        """
        try:
            ip_obj = ipaddress.ip_address(ip)
            return ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local
        except ValueError:
            return False

    def _check_internal_url(self) -> bool:
        """
        Check if URL points to internal network

        Returns:
            True if URL resolves to internal IP
        """
        parsed = urlparse(self.url)
        hostname = parsed.hostname or ""

        # Check if hostname is directly an IP address
        try:
            if self._is_private_ip(hostname):
                return True
        except ValueError:
            pass

        # Try to resolve hostname to IP
        try:
            ip = socket.gethostbyname(hostname)
            return self._is_private_ip(ip)
        except socket.gaierror:
            # Cannot resolve, assume external
            return False

    def _unset_proxies(self) -> dict[str, str] | None:
        keys = [
            "http_proxy",
            "https_proxy",
            "HTTP_PROXY",
            "HTTPS_PROXY",
            "all_proxy",
            "ALL_PROXY",
        ]
        for env_key in keys:
            os.environ.pop(env_key, None)
        return None

    def _request(
        self,
        method: str,
        endpoint: str,
        data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """
        Send HTTP request

        Args:
            method: HTTP method (GET, POST, DELETE)
            endpoint: API endpoint
            data: Request body data
            params: Query parameters

        Returns:
            Response data
        """
        url = f"{self.url}/api{endpoint}"

        response = self.session.request(
            method=method,
            url=url,
            json=data,
            params=params,
            timeout=self.timeout,
            headers=self.headers,
            verify=self.verify_ssl,
        )

        response.raise_for_status()

        # Check if there is response content
        if response.text:
            return response.json()
        return None

    # ==================== System Status ====================

    def check_api(self) -> dict[str, Any]:
        """Check if API is running normally"""
        return self._request("GET", "/")

    def get_config(self) -> dict[str, Any]:
        """Get current configuration information"""
        return self._request("GET", "/config")

    def get_components(self) -> list[str]:
        """Get list of loaded components"""
        return self._request("GET", "/components")

    def get_events(self) -> list[dict[str, Any]]:
        """Get list of events"""
        return self._request("GET", "/events")

    def get_services(self) -> list[dict[str, Any]]:
        """Get list of services"""
        return self._request("GET", "/services")

    # ==================== Entity States ====================

    def get_states(self) -> list[dict[str, Any]]:
        """Get all entity states"""
        return self._request("GET", "/states")

    def get_entity(self, entity_id: str) -> dict[str, Any]:
        """
        Get specific entity state

        Args:
            entity_id: Entity ID (e.g. light.living_room)

        Returns:
            Entity state object
        """
        return self._request("GET", f"/states/{entity_id}")

    def set_state(
        self, entity_id: str, state: str, attributes: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Update or create entity state

        Note: This operation only updates the device state representation in HA,
              it does not communicate with the actual device

        Args:
            entity_id: Entity ID
            state: State value
            attributes: Attributes dictionary

        Returns:
            Updated state object
        """
        data: dict[str, Any] = {"state": state}
        if attributes:
            data["attributes"] = attributes
        return self._request("POST", f"/states/{entity_id}", data=data)

    def delete_entity(self, entity_id: str) -> None:
        """
        Delete entity

        Args:
            entity_id: Entity ID
        """
        self._request("DELETE", f"/states/{entity_id}")

    def list_entities(self, available_only: bool = False) -> list[str]:
        """
        List all entities with ID, state and friendly name

        Args:
            available_only: If True, filter out entities with state "unavailable"

        Returns:
            List of strings: "entity_id state friendly_name"
        """
        states = self.get_states()
        result = []
        for state in states:
            entity_id = state["entity_id"]
            entity_state = state["state"]

            # Filter unavailable entities if requested
            if available_only and entity_state == "unavailable":
                continue

            friendly_name = state.get("attributes", {}).get("friendly_name", "")
            friendly_name = "_".join(friendly_name.strip().split())
            entity_state = "_".join(entity_state.strip().split())
            result.append(f"{entity_id} {entity_state} {friendly_name}")
        return result

    def get_live_context(self) -> list[dict[str, Any]]:
        """
        Get live context of all entities (formatted output)

        Returns:
            List of entities with name, domain, state, attributes
        """
        states = self.get_states()
        return [
            {
                "name": state["entity_id"],
                "domain": state["entity_id"].split(".")[0],
                "state": state["state"],
                "attributes": state["attributes"],
            }
            for state in states
        ]

    def get_entities_by_domain(self, domain: str) -> list[dict[str, Any]]:
        """
        Get all entities for a specific domain

        Args:
            domain: Entity domain (e.g. scene, automation, todo)

        Returns:
            List of entity state objects
        """
        return [
            state
            for state in self.get_states()
            if state.get("entity_id", "").startswith(f"{domain}.")
        ]

    # ==================== Service Calls ====================

    def call_service(
        self,
        domain: str,
        service: str,
        entity_id: str | None = None,
        return_response: bool = False,
        **kwargs: Any,
    ) -> Any:
        """
        Call a service

        Args:
            domain: Service domain (e.g. light, switch)
            service: Service name (e.g. turn_on, turn_off)
            entity_id: Entity ID (optional, if service requires)
            return_response: Whether to return response data
            **kwargs: Additional service parameters

        Returns:
            Service response (if return_response=True)
        """
        data: dict[str, Any] = kwargs
        if entity_id:
            data["entity_id"] = entity_id

        endpoint = f"/services/{domain}/{service}"
        params = {"return_response": ""} if return_response else None

        return self._request("POST", endpoint, data=data, params=params)

    # ==================== Scene Helpers ====================

    def get_scenes(self) -> list[dict[str, Any]]:
        """Get all scene entities"""
        return self.get_entities_by_domain("scene")

    def activate_scene(self, entity_id: str, transition: float | None = None) -> Any:
        """
        Activate a scene

        Args:
            entity_id: Scene entity ID
            transition: Optional transition duration in seconds
        """
        data: dict[str, Any] = {}
        if transition is not None:
            data["transition"] = transition
        return self.call_service("scene", "turn_on", entity_id=entity_id, **data)

    def apply_scene(
        self, entities: dict[str, Any], transition: float | None = None
    ) -> Any:
        """
        Apply an ad-hoc scene definition

        Args:
            entities: Scene entity definitions keyed by entity_id
            transition: Optional transition duration in seconds
        """
        data: dict[str, Any] = {"entities": entities}
        if transition is not None:
            data["transition"] = transition
        return self.call_service("scene", "apply", **data)

    def create_scene(
        self,
        scene_id: str,
        entities: dict[str, Any] | None = None,
        snapshot_entities: list[str] | None = None,
    ) -> Any:
        """
        Create a dynamic scene

        Args:
            scene_id: Scene ID without domain prefix
            entities: Optional explicit entity state definitions
            snapshot_entities: Optional entities to snapshot current state from
        """
        if not entities and not snapshot_entities:
            raise ValueError("scene.create requires --entities or --snapshot-entities")

        data: dict[str, Any] = {"scene_id": scene_id}
        if entities:
            data["entities"] = entities
        if snapshot_entities:
            data["snapshot_entities"] = snapshot_entities
        return self.call_service("scene", "create", **data)

    def delete_scene(self, entity_id: str) -> Any:
        """
        Delete a dynamically created scene

        Args:
            entity_id: Scene entity ID
        """
        return self.call_service("scene", "delete", entity_id=entity_id)

    def reload_scenes(self) -> Any:
        """Reload scenes"""
        return self.call_service("scene", "reload")

    # ==================== Automation Helpers ====================

    def get_automations(self) -> list[dict[str, Any]]:
        """Get all automation entities"""
        return self.get_entities_by_domain("automation")

    def trigger_automation(
        self,
        entity_id: str,
        skip_condition: bool = False,
        variables: dict[str, Any] | None = None,
    ) -> Any:
        """
        Trigger an automation manually

        Args:
            entity_id: Automation entity ID
            skip_condition: Whether to skip condition checks
            variables: Optional run variables
        """
        data: dict[str, Any] = {}
        if skip_condition:
            data["skip_condition"] = True
        if variables:
            data["variables"] = variables
        return self.call_service("automation", "trigger", entity_id=entity_id, **data)

    def turn_on_automation(self, entity_id: str) -> Any:
        """Enable an automation"""
        return self.call_service("automation", "turn_on", entity_id=entity_id)

    def turn_off_automation(self, entity_id: str, stop_actions: bool = False) -> Any:
        """
        Disable an automation

        Args:
            entity_id: Automation entity ID
            stop_actions: Whether to stop currently running actions
        """
        data: dict[str, Any] = {}
        if stop_actions:
            data["stop_actions"] = True
        return self.call_service("automation", "turn_off", entity_id=entity_id, **data)

    def toggle_automation(self, entity_id: str) -> Any:
        """Toggle automation enabled state"""
        return self.call_service("automation", "toggle", entity_id=entity_id)

    def reload_automations(self) -> Any:
        """Reload automations"""
        return self.call_service("automation", "reload")

    # ==================== Todo Helpers ====================

    def get_todo_lists(self) -> list[dict[str, Any]]:
        """Get all to-do list entities"""
        return self.get_entities_by_domain("todo")

    def get_scripts(self) -> list[dict[str, Any]]:
        """Get all script entities"""
        return self.get_entities_by_domain("script")

    def get_input_booleans(self) -> list[dict[str, Any]]:
        """Get all input_boolean entities"""
        return self.get_entities_by_domain("input_boolean")

    def get_input_selects(self) -> list[dict[str, Any]]:
        """Get all input_select entities"""
        return self.get_entities_by_domain("input_select")

    # ==================== Script Helpers ====================

    def run_script(
        self,
        entity_id: str,
        variables: dict[str, Any] | None = None,
        return_response: bool = False,
    ) -> Any:
        """
        Run a script entity

        Args:
            entity_id: Script entity ID
            variables: Optional script variables
            return_response: Whether to request service response data
        """
        data: dict[str, Any] = {}
        if variables:
            data.update(variables)
        return self.call_service(
            "script",
            "turn_on",
            entity_id=entity_id,
            return_response=return_response,
            **data,
        )

    def turn_off_script(self, entity_id: str) -> Any:
        """Turn off a running script"""
        return self.call_service("script", "turn_off", entity_id=entity_id)

    def toggle_script(self, entity_id: str) -> Any:
        """Toggle a script entity"""
        return self.call_service("script", "toggle", entity_id=entity_id)

    def reload_scripts(self) -> Any:
        """Reload script configuration"""
        return self.call_service("script", "reload")

    # ==================== Input Boolean Helpers ====================

    def turn_on_input_boolean(self, entity_id: str) -> Any:
        """Turn on an input_boolean"""
        return self.call_service("input_boolean", "turn_on", entity_id=entity_id)

    def turn_off_input_boolean(self, entity_id: str) -> Any:
        """Turn off an input_boolean"""
        return self.call_service("input_boolean", "turn_off", entity_id=entity_id)

    def toggle_input_boolean(self, entity_id: str) -> Any:
        """Toggle an input_boolean"""
        return self.call_service("input_boolean", "toggle", entity_id=entity_id)

    def reload_input_booleans(self) -> Any:
        """Reload input_boolean configuration"""
        return self.call_service("input_boolean", "reload")

    # ==================== Input Select Helpers ====================

    def select_input_option(self, entity_id: str, option: str) -> Any:
        """
        Select an input_select option

        Args:
            entity_id: Input select entity ID
            option: Option value to select
        """
        return self.call_service(
            "input_select", "select_option", entity_id=entity_id, option=option
        )

    def select_next_input_option(self, entity_id: str, cycle: bool = True) -> Any:
        """
        Select the next input_select option

        Args:
            entity_id: Input select entity ID
            cycle: Whether to wrap to the start at the end
        """
        return self.call_service(
            "input_select", "select_next", entity_id=entity_id, cycle=cycle
        )

    def select_previous_input_option(self, entity_id: str, cycle: bool = True) -> Any:
        """
        Select the previous input_select option

        Args:
            entity_id: Input select entity ID
            cycle: Whether to wrap to the end at the start
        """
        return self.call_service(
            "input_select", "select_previous", entity_id=entity_id, cycle=cycle
        )

    def set_input_select_options(self, entity_id: str, options: list[str]) -> Any:
        """
        Replace input_select options

        Args:
            entity_id: Input select entity ID
            options: New list of options
        """
        return self.call_service(
            "input_select", "set_options", entity_id=entity_id, options=options
        )

    def reload_input_selects(self) -> Any:
        """Reload input_select configuration"""
        return self.call_service("input_select", "reload")

    def _validate_todo_due_fields(
        self, due_date: str | None = None, due_datetime: str | None = None
    ) -> None:
        if due_date and due_datetime:
            raise ValueError("Only one of due_date or due_datetime may be provided")

    def get_todo_items(
        self, entity_id: str, status: str | list[str] | None = None
    ) -> Any:
        """
        Get items from a to-do list

        Args:
            entity_id: Todo entity ID
            status: Optional item status filter(s)
        """
        data: dict[str, Any] = {}
        if status is not None:
            data["status"] = status
        return self.call_service(
            "todo",
            "get_items",
            entity_id=entity_id,
            return_response=True,
            **data,
        )

    def add_todo_item(
        self,
        entity_id: str,
        item: str,
        due_date: str | None = None,
        due_datetime: str | None = None,
        description: str | None = None,
    ) -> Any:
        """
        Add an item to a to-do list

        Args:
            entity_id: Todo entity ID
            item: Item summary
            due_date: Optional due date
            due_datetime: Optional due datetime
            description: Optional description
        """
        self._validate_todo_due_fields(due_date, due_datetime)
        data: dict[str, Any] = {"item": item}
        if due_date:
            data["due_date"] = due_date
        if due_datetime:
            data["due_datetime"] = due_datetime
        if description:
            data["description"] = description
        return self.call_service("todo", "add_item", entity_id=entity_id, **data)

    def update_todo_item(
        self,
        entity_id: str,
        item: str,
        rename: str | None = None,
        status: str | None = None,
        due_date: str | None = None,
        due_datetime: str | None = None,
        description: str | None = None,
    ) -> Any:
        """
        Update a to-do list item

        Args:
            entity_id: Todo entity ID
            item: Item summary or UID
            rename: Optional new summary
            status: Optional item status
            due_date: Optional due date
            due_datetime: Optional due datetime
            description: Optional description
        """
        self._validate_todo_due_fields(due_date, due_datetime)
        if not any([rename, status, due_date, due_datetime, description]):
            raise ValueError("todo.update_item requires at least one field to update")

        data: dict[str, Any] = {"item": item}
        if rename:
            data["rename"] = rename
        if status:
            data["status"] = status
        if due_date:
            data["due_date"] = due_date
        if due_datetime:
            data["due_datetime"] = due_datetime
        if description:
            data["description"] = description
        return self.call_service("todo", "update_item", entity_id=entity_id, **data)

    def remove_todo_item(self, entity_id: str, item: str) -> Any:
        """
        Remove a to-do list item

        Args:
            entity_id: Todo entity ID
            item: Item summary or UID
        """
        return self.call_service("todo", "remove_item", entity_id=entity_id, item=item)

    def remove_completed_todo_items(self, entity_id: str) -> Any:
        """Remove all completed items from a to-do list"""
        return self.call_service("todo", "remove_completed_items", entity_id=entity_id)

    # ==================== Events ====================

    def fire_event(
        self, event_type: str, event_data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Fire an event

        Args:
            event_type: Event type
            event_data: Event data

        Returns:
            Response data
        """
        return self._request("POST", f"/events/{event_type}", data=event_data)

    # ==================== History ====================

    def get_history(
        self,
        entity_ids: list[str],
        timestamp: str | None = None,
        end_time: str | None = None,
        minimal_response: bool = False,
        no_attributes: bool = False,
        significant_changes_only: bool = False,
    ) -> list[Any]:
        """
        Get state history

        Args:
            entity_ids: List of entity IDs
            timestamp: Start timestamp
            end_time: End time
            minimal_response: Only return last change and state
            no_attributes: Skip attributes
            significant_changes_only: Only return significant changes

        Returns:
            List of history records
        """
        endpoint = f"/history/period/{timestamp}" if timestamp else "/history/period"

        params = {"filter_entity_id": ",".join(entity_ids)}
        if end_time:
            params["end_time"] = end_time
        if minimal_response:
            params["minimal_response"] = ""
        if no_attributes:
            params["no_attributes"] = ""
        if significant_changes_only:
            params["significant_changes_only"] = ""

        return self._request("GET", endpoint, params=params)

    # ==================== Logbook ====================

    def get_logbook(
        self,
        timestamp: str | None = None,
        entity: str | None = None,
        end_time: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get logbook entries

        Args:
            timestamp: Start timestamp
            entity: Filter entity ID
            end_time: End time

        Returns:
            List of logbook entries
        """
        endpoint = f"/logbook/{timestamp}" if timestamp else "/logbook"

        params = {}
        if entity:
            params["entity"] = entity
        if end_time:
            params["end_time"] = end_time

        return self._request("GET", endpoint, params=params)

    # ==================== Template Rendering ====================

    def render_template(self, template: str) -> str:
        """
        Render Home Assistant template

        Args:
            template: Template string

        Returns:
            Rendered text
        """
        data = {"template": template}
        response = self.session.post(
            f"{self.url}/api/template",
            json=data,
            timeout=self.timeout,
            verify=self.verify_ssl,
        )
        response.raise_for_status()
        return response.text

    # ==================== Camera ====================

    def get_camera_image(self, entity_id: str, timestamp: str | None = None) -> bytes:
        """
        Get camera image

        Args:
            entity_id: Camera entity ID
            timestamp: Timestamp (optional)

        Returns:
            Image binary data
        """
        endpoint = f"/camera_proxy/{entity_id}"
        params = {"time": timestamp} if timestamp else None

        response = self.session.get(
            f"{self.url}/api{endpoint}",
            params=params,
            timeout=self.timeout,
            verify=self.verify_ssl,
        )
        response.raise_for_status()
        return response.content

    # ==================== Calendar ====================

    def get_calendars(self) -> list[dict[str, Any]]:
        """Get list of calendar entities"""
        return self._request("GET", "/calendars")

    def get_calendar_events(
        self, entity_id: str, start: str, end: str
    ) -> list[dict[str, Any]]:
        """
        Get calendar events

        Args:
            entity_id: Calendar entity ID
            start: Start time
            end: End time

        Returns:
            List of events
        """
        return self._request(
            "GET", f"/calendars/{entity_id}", params={"start": start, "end": end}
        )

    # ==================== Error Log ====================

    def get_error_log(self) -> str:
        """Get error log"""
        response = self.session.get(
            f"{self.url}/api/error_log",
            timeout=self.timeout,
            verify=self.verify_ssl,
        )
        response.raise_for_status()
        return response.text

    # ==================== Configuration Check ====================

    def check_config(self) -> dict[str, Any]:
        """Check configuration file"""
        return self._request("POST", "/config/core/check_config")

    # ==================== Intent Handling ====================

    def handle_intent(
        self, name: str, data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Handle intent

        Args:
            name: Intent name
            data: Intent data

        Returns:
            Processing result
        """
        payload: dict[str, Any] = {"name": name}
        if data:
            payload["data"] = data
        return self._request("POST", "/intent/handle", data=payload)

    def close(self) -> None:
        """Close session"""
        self.session.close()

    def __enter__(self) -> "HomeAssistantAPI":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()


# ==================== Command Line Tool ====================


def main():
    """Command line entry point"""
    import argparse

    def parse_json_arg(raw: str | None, flag_name: str) -> dict[str, Any]:
        if not raw:
            return {}
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON for {flag_name}: {exc}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"{flag_name} must decode to a JSON object")
        return value

    def print_json(data: Any) -> None:
        print(json.dumps(data, indent=2, ensure_ascii=False))

    parser = argparse.ArgumentParser(description="Home Assistant REST API client")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    subparsers.add_parser("check-api", help="Check if API is running")
    subparsers.add_parser("get-config", help="Get configuration information")
    subparsers.add_parser("get-components", help="Get loaded components")
    subparsers.add_parser("get-events", help="Get registered event types")
    subparsers.add_parser("get-services", help="Get available services")
    subparsers.add_parser("get-states", help="Get all entity states")
    subparsers.add_parser("get-scenes", help="Get scene entities")
    subparsers.add_parser("get-automations", help="Get automation entities")
    subparsers.add_parser("get-todo-lists", help="Get to-do list entities")
    subparsers.add_parser("get-scripts", help="Get script entities")
    subparsers.add_parser("get-input-booleans", help="Get input_boolean entities")
    subparsers.add_parser("get-input-selects", help="Get input_select entities")

    # Get entity state
    get_entity_parser = subparsers.add_parser("get-entity", help="Get entity state")
    get_entity_parser.add_argument("entity_id", help="Entity ID")

    # Set entity state
    set_state_parser = subparsers.add_parser("set-state", help="Set entity state")
    set_state_parser.add_argument("entity_id", help="Entity ID")
    set_state_parser.add_argument("state", help="State value")
    set_state_parser.add_argument(
        "--attributes", help="State attributes in JSON format"
    )

    # Delete entity state
    delete_entity_parser = subparsers.add_parser(
        "delete-entity", help="Delete entity state"
    )
    delete_entity_parser.add_argument("entity_id", help="Entity ID")

    # List all entities
    list_entities_parser = subparsers.add_parser(
        "list-entities", help="List all entity ID state and friendly name"
    )
    list_entities_parser.add_argument(
        "--domain", help="Only list entities from this domain"
    )

    # List available entities
    list_available_parser = subparsers.add_parser(
        "list-available-entities", help="List available entities (exclude unavailable)"
    )
    list_available_parser.add_argument(
        "--domain", help="Only list entities from this domain"
    )

    # Get live context
    subparsers.add_parser("live-context", help="Get live context of all entities")

    # Scene helpers
    activate_scene_parser = subparsers.add_parser(
        "activate-scene", help="Activate a scene"
    )
    activate_scene_parser.add_argument("entity_id", help="Scene entity ID")
    activate_scene_parser.add_argument(
        "--transition", type=float, help="Transition duration in seconds"
    )

    apply_scene_parser = subparsers.add_parser(
        "apply-scene", help="Apply a scene definition directly"
    )
    apply_scene_parser.add_argument(
        "--entities", required=True, help="Scene entities in JSON format"
    )
    apply_scene_parser.add_argument(
        "--transition", type=float, help="Transition duration in seconds"
    )

    create_scene_parser = subparsers.add_parser(
        "create-scene", help="Create a dynamic scene"
    )
    create_scene_parser.add_argument("scene_id", help="Scene ID without domain")
    create_scene_parser.add_argument("--entities", help="Scene entities in JSON format")
    create_scene_parser.add_argument(
        "--snapshot-entities",
        nargs="+",
        help="Entity IDs to snapshot into the scene",
    )

    delete_scene_parser = subparsers.add_parser(
        "delete-scene", help="Delete a dynamic scene"
    )
    delete_scene_parser.add_argument("entity_id", help="Scene entity ID")
    subparsers.add_parser("reload-scenes", help="Reload scene configuration")

    # Automation helpers
    trigger_automation_parser = subparsers.add_parser(
        "trigger-automation", help="Trigger an automation"
    )
    trigger_automation_parser.add_argument("entity_id", help="Automation entity ID")
    trigger_automation_parser.add_argument(
        "--skip-condition",
        action="store_true",
        help="Skip automation condition checks",
    )
    trigger_automation_parser.add_argument(
        "--variables", help="Automation variables in JSON format"
    )

    automation_entity_parser = subparsers.add_parser(
        "turn-on-automation", help="Enable an automation"
    )
    automation_entity_parser.add_argument("entity_id", help="Automation entity ID")

    turn_off_automation_parser = subparsers.add_parser(
        "turn-off-automation", help="Disable an automation"
    )
    turn_off_automation_parser.add_argument("entity_id", help="Automation entity ID")
    turn_off_automation_parser.add_argument(
        "--stop-actions",
        action="store_true",
        help="Stop currently running actions",
    )

    toggle_automation_parser = subparsers.add_parser(
        "toggle-automation", help="Toggle automation enabled state"
    )
    toggle_automation_parser.add_argument("entity_id", help="Automation entity ID")
    subparsers.add_parser("reload-automations", help="Reload automation configuration")

    # Todo helpers
    get_todo_items_parser = subparsers.add_parser(
        "get-todo-items", help="Get to-do list items"
    )
    get_todo_items_parser.add_argument("entity_id", help="Todo entity ID")
    get_todo_items_parser.add_argument(
        "--status",
        nargs="+",
        help="Optional item status filter(s), e.g. needs_action completed",
    )

    add_todo_item_parser = subparsers.add_parser(
        "add-todo-item", help="Add an item to a to-do list"
    )
    add_todo_item_parser.add_argument("entity_id", help="Todo entity ID")
    add_todo_item_parser.add_argument("item", help="Item summary")
    add_todo_item_parser.add_argument("--due-date", help="Due date (YYYY-MM-DD)")
    add_todo_item_parser.add_argument("--due-datetime", help="Due datetime")
    add_todo_item_parser.add_argument("--description", help="Item description")

    update_todo_item_parser = subparsers.add_parser(
        "update-todo-item", help="Update a to-do list item"
    )
    update_todo_item_parser.add_argument("entity_id", help="Todo entity ID")
    update_todo_item_parser.add_argument("item", help="Item summary or UID")
    update_todo_item_parser.add_argument("--rename", help="Rename the item")
    update_todo_item_parser.add_argument(
        "--status", choices=["needs_action", "completed"], help="New item status"
    )
    update_todo_item_parser.add_argument("--due-date", help="Due date (YYYY-MM-DD)")
    update_todo_item_parser.add_argument("--due-datetime", help="Due datetime")
    update_todo_item_parser.add_argument("--description", help="Item description")

    remove_todo_item_parser = subparsers.add_parser(
        "remove-todo-item", help="Remove a to-do list item"
    )
    remove_todo_item_parser.add_argument("entity_id", help="Todo entity ID")
    remove_todo_item_parser.add_argument("item", help="Item summary or UID")

    clear_completed_todo_parser = subparsers.add_parser(
        "clear-completed-todo", help="Remove completed items from a to-do list"
    )
    clear_completed_todo_parser.add_argument("entity_id", help="Todo entity ID")

    # Script helpers
    run_script_parser = subparsers.add_parser("run-script", help="Run a script entity")
    run_script_parser.add_argument("entity_id", help="Script entity ID")
    run_script_parser.add_argument(
        "--variables", help="Script variables in JSON format"
    )
    run_script_parser.add_argument(
        "--return-response", action="store_true", help="Return service response data"
    )

    turn_off_script_parser = subparsers.add_parser(
        "turn-off-script", help="Turn off a running script"
    )
    turn_off_script_parser.add_argument("entity_id", help="Script entity ID")

    toggle_script_parser = subparsers.add_parser(
        "toggle-script", help="Toggle a script entity"
    )
    toggle_script_parser.add_argument("entity_id", help="Script entity ID")
    subparsers.add_parser("reload-scripts", help="Reload script configuration")

    # Input boolean helpers
    turn_on_input_boolean_parser = subparsers.add_parser(
        "turn-on-input-boolean", help="Turn on an input_boolean"
    )
    turn_on_input_boolean_parser.add_argument(
        "entity_id", help="Input boolean entity ID"
    )

    turn_off_input_boolean_parser = subparsers.add_parser(
        "turn-off-input-boolean", help="Turn off an input_boolean"
    )
    turn_off_input_boolean_parser.add_argument(
        "entity_id", help="Input boolean entity ID"
    )

    toggle_input_boolean_parser = subparsers.add_parser(
        "toggle-input-boolean", help="Toggle an input_boolean"
    )
    toggle_input_boolean_parser.add_argument(
        "entity_id", help="Input boolean entity ID"
    )
    subparsers.add_parser(
        "reload-input-booleans", help="Reload input_boolean configuration"
    )

    # Input select helpers
    select_input_option_parser = subparsers.add_parser(
        "select-input-option", help="Select an input_select option"
    )
    select_input_option_parser.add_argument("entity_id", help="Input select entity ID")
    select_input_option_parser.add_argument("option", help="Option to select")

    select_next_input_option_parser = subparsers.add_parser(
        "select-next-input-option", help="Select next input_select option"
    )
    select_next_input_option_parser.add_argument(
        "entity_id", help="Input select entity ID"
    )
    select_next_input_option_parser.add_argument(
        "--no-cycle",
        action="store_true",
        help="Do not wrap around when reaching the end",
    )

    select_previous_input_option_parser = subparsers.add_parser(
        "select-previous-input-option", help="Select previous input_select option"
    )
    select_previous_input_option_parser.add_argument(
        "entity_id", help="Input select entity ID"
    )
    select_previous_input_option_parser.add_argument(
        "--no-cycle",
        action="store_true",
        help="Do not wrap around when reaching the start",
    )

    set_input_select_options_parser = subparsers.add_parser(
        "set-input-select-options", help="Replace input_select options"
    )
    set_input_select_options_parser.add_argument(
        "entity_id", help="Input select entity ID"
    )
    set_input_select_options_parser.add_argument(
        "options",
        nargs="+",
        help="New option values",
    )
    subparsers.add_parser(
        "reload-input-selects", help="Reload input_select configuration"
    )

    # Call service
    call_service_parser = subparsers.add_parser("call-service", help="Call service")
    call_service_parser.add_argument("domain", help="Service domain")
    call_service_parser.add_argument("service", help="Service name")
    call_service_parser.add_argument("--entity-id", help="Entity ID")
    call_service_parser.add_argument("--data", help="Service data in JSON format")
    call_service_parser.add_argument(
        "--return-response", action="store_true", help="Return service response data"
    )

    # Fire event
    fire_event_parser = subparsers.add_parser("fire-event", help="Fire an event")
    fire_event_parser.add_argument("event_type", help="Event type")
    fire_event_parser.add_argument("--data", help="Event data in JSON format")

    # History
    history_parser = subparsers.add_parser(
        "get-history", help="Get entity state history"
    )
    history_parser.add_argument("entity_ids", nargs="+", help="One or more entity IDs")
    history_parser.add_argument("--timestamp", help="Start timestamp")
    history_parser.add_argument("--end-time", help="End timestamp")
    history_parser.add_argument(
        "--minimal-response",
        action="store_true",
        help="Only return last change and state",
    )
    history_parser.add_argument(
        "--no-attributes", action="store_true", help="Exclude attributes"
    )
    history_parser.add_argument(
        "--significant-changes-only",
        action="store_true",
        help="Only return significant changes",
    )

    # Logbook
    logbook_parser = subparsers.add_parser("get-logbook", help="Get logbook entries")
    logbook_parser.add_argument("--timestamp", help="Start timestamp")
    logbook_parser.add_argument("--entity", help="Filter by entity ID")
    logbook_parser.add_argument("--end-time", help="End timestamp")

    # Template rendering
    template_parser = subparsers.add_parser(
        "render-template", help="Render Home Assistant template"
    )
    template_group = template_parser.add_mutually_exclusive_group(required=True)
    template_group.add_argument("template", nargs="?", help="Inline template string")
    template_group.add_argument("--file", help="Read template from file")

    # Camera image
    camera_parser = subparsers.add_parser("get-camera-image", help="Fetch camera image")
    camera_parser.add_argument("entity_id", help="Camera entity ID")
    camera_parser.add_argument("--timestamp", help="Image timestamp")
    camera_parser.add_argument("--output", help="Write image to file instead of stdout")

    # Calendars
    subparsers.add_parser("get-calendars", help="Get calendar entities")

    calendar_events_parser = subparsers.add_parser(
        "get-calendar-events", help="Get calendar events"
    )
    calendar_events_parser.add_argument("entity_id", help="Calendar entity ID")
    calendar_events_parser.add_argument("start", help="Start time")
    calendar_events_parser.add_argument("end", help="End time")

    # System helpers
    subparsers.add_parser("get-error-log", help="Get Home Assistant error log")
    subparsers.add_parser("check-config", help="Check Home Assistant configuration")

    # Intent handling
    intent_parser = subparsers.add_parser(
        "handle-intent", help="Handle Home Assistant intent"
    )
    intent_parser.add_argument("name", help="Intent name")
    intent_parser.add_argument("--data", help="Intent data in JSON format")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        with HomeAssistantAPI() as ha:
            if args.command == "check-api":
                print_json(ha.check_api())

            elif args.command == "get-config":
                print_json(ha.get_config())

            elif args.command == "get-components":
                print_json(ha.get_components())

            elif args.command == "get-events":
                print_json(ha.get_events())

            elif args.command == "get-services":
                print_json(ha.get_services())

            elif args.command == "get-states":
                print_json(ha.get_states())

            elif args.command == "get-scenes":
                print_json(ha.get_scenes())

            elif args.command == "get-automations":
                print_json(ha.get_automations())

            elif args.command == "get-todo-lists":
                print_json(ha.get_todo_lists())

            elif args.command == "get-scripts":
                print_json(ha.get_scripts())

            elif args.command == "get-input-booleans":
                print_json(ha.get_input_booleans())

            elif args.command == "get-input-selects":
                print_json(ha.get_input_selects())

            elif args.command == "get-entity":
                result = ha.get_entity(args.entity_id)
                print_json(result)

            elif args.command == "set-state":
                attributes = parse_json_arg(args.attributes, "--attributes")
                print_json(
                    ha.set_state(
                        args.entity_id, args.state, attributes=attributes or None
                    )
                )

            elif args.command == "delete-entity":
                ha.delete_entity(args.entity_id)
                print(f"Deleted {args.entity_id}")

            elif args.command == "list-entities":
                entities = ha.list_entities()
                for entity in entities:
                    if args.domain and not entity.startswith(f"{args.domain}."):
                        continue
                    print(entity)

            elif args.command == "list-available-entities":
                entities = ha.list_entities(available_only=True)
                for entity in entities:
                    if args.domain and not entity.startswith(f"{args.domain}."):
                        continue
                    print(entity)

            elif args.command == "live-context":
                context = ha.get_live_context()
                print_json(context)

            elif args.command == "activate-scene":
                result = ha.activate_scene(args.entity_id, transition=args.transition)
                if result:
                    print_json(result)

            elif args.command == "apply-scene":
                entities = parse_json_arg(args.entities, "--entities")
                result = ha.apply_scene(entities, transition=args.transition)
                if result:
                    print_json(result)

            elif args.command == "create-scene":
                entities = parse_json_arg(args.entities, "--entities")
                result = ha.create_scene(
                    args.scene_id,
                    entities=entities or None,
                    snapshot_entities=args.snapshot_entities,
                )
                if result:
                    print_json(result)

            elif args.command == "delete-scene":
                result = ha.delete_scene(args.entity_id)
                if result:
                    print_json(result)

            elif args.command == "reload-scenes":
                result = ha.reload_scenes()
                if result:
                    print_json(result)

            elif args.command == "trigger-automation":
                variables = parse_json_arg(args.variables, "--variables")
                result = ha.trigger_automation(
                    args.entity_id,
                    skip_condition=args.skip_condition,
                    variables=variables or None,
                )
                if result:
                    print_json(result)

            elif args.command == "turn-on-automation":
                result = ha.turn_on_automation(args.entity_id)
                if result:
                    print_json(result)

            elif args.command == "turn-off-automation":
                result = ha.turn_off_automation(
                    args.entity_id, stop_actions=args.stop_actions
                )
                if result:
                    print_json(result)

            elif args.command == "toggle-automation":
                result = ha.toggle_automation(args.entity_id)
                if result:
                    print_json(result)

            elif args.command == "reload-automations":
                result = ha.reload_automations()
                if result:
                    print_json(result)

            elif args.command == "get-todo-items":
                statuses: str | list[str] | None = args.status
                if statuses and len(statuses) == 1:
                    statuses = statuses[0]
                print_json(ha.get_todo_items(args.entity_id, status=statuses))

            elif args.command == "add-todo-item":
                result = ha.add_todo_item(
                    args.entity_id,
                    args.item,
                    due_date=args.due_date,
                    due_datetime=args.due_datetime,
                    description=args.description,
                )
                if result:
                    print_json(result)

            elif args.command == "update-todo-item":
                result = ha.update_todo_item(
                    args.entity_id,
                    args.item,
                    rename=args.rename,
                    status=args.status,
                    due_date=args.due_date,
                    due_datetime=args.due_datetime,
                    description=args.description,
                )
                if result:
                    print_json(result)

            elif args.command == "remove-todo-item":
                result = ha.remove_todo_item(args.entity_id, args.item)
                if result:
                    print_json(result)

            elif args.command == "clear-completed-todo":
                result = ha.remove_completed_todo_items(args.entity_id)
                if result:
                    print_json(result)

            elif args.command == "run-script":
                variables = parse_json_arg(args.variables, "--variables")
                result = ha.run_script(
                    args.entity_id,
                    variables=variables or None,
                    return_response=args.return_response,
                )
                if result:
                    print_json(result)

            elif args.command == "turn-off-script":
                result = ha.turn_off_script(args.entity_id)
                if result:
                    print_json(result)

            elif args.command == "toggle-script":
                result = ha.toggle_script(args.entity_id)
                if result:
                    print_json(result)

            elif args.command == "reload-scripts":
                result = ha.reload_scripts()
                if result:
                    print_json(result)

            elif args.command == "turn-on-input-boolean":
                result = ha.turn_on_input_boolean(args.entity_id)
                if result:
                    print_json(result)

            elif args.command == "turn-off-input-boolean":
                result = ha.turn_off_input_boolean(args.entity_id)
                if result:
                    print_json(result)

            elif args.command == "toggle-input-boolean":
                result = ha.toggle_input_boolean(args.entity_id)
                if result:
                    print_json(result)

            elif args.command == "reload-input-booleans":
                result = ha.reload_input_booleans()
                if result:
                    print_json(result)

            elif args.command == "select-input-option":
                result = ha.select_input_option(args.entity_id, args.option)
                if result:
                    print_json(result)

            elif args.command == "select-next-input-option":
                result = ha.select_next_input_option(
                    args.entity_id, cycle=not args.no_cycle
                )
                if result:
                    print_json(result)

            elif args.command == "select-previous-input-option":
                result = ha.select_previous_input_option(
                    args.entity_id, cycle=not args.no_cycle
                )
                if result:
                    print_json(result)

            elif args.command == "set-input-select-options":
                result = ha.set_input_select_options(args.entity_id, args.options)
                if result:
                    print_json(result)

            elif args.command == "reload-input-selects":
                result = ha.reload_input_selects()
                if result:
                    print_json(result)

            elif args.command == "call-service":
                data = parse_json_arg(args.data, "--data")
                result = ha.call_service(
                    args.domain,
                    args.service,
                    entity_id=args.entity_id,
                    return_response=args.return_response,
                    **data,
                )
                if result:
                    print_json(result)

            elif args.command == "fire-event":
                data = parse_json_arg(args.data, "--data")
                print_json(ha.fire_event(args.event_type, data or None))

            elif args.command == "get-history":
                print_json(
                    ha.get_history(
                        args.entity_ids,
                        timestamp=args.timestamp,
                        end_time=args.end_time,
                        minimal_response=args.minimal_response,
                        no_attributes=args.no_attributes,
                        significant_changes_only=args.significant_changes_only,
                    )
                )

            elif args.command == "get-logbook":
                print_json(
                    ha.get_logbook(
                        timestamp=args.timestamp,
                        entity=args.entity,
                        end_time=args.end_time,
                    )
                )

            elif args.command == "render-template":
                template = args.template
                if args.file:
                    with open(args.file, "r", encoding="utf-8") as file_handle:
                        template = file_handle.read()
                print(ha.render_template(template))

            elif args.command == "get-camera-image":
                image = ha.get_camera_image(args.entity_id, timestamp=args.timestamp)
                if args.output:
                    with open(args.output, "wb") as file_handle:
                        file_handle.write(image)
                    print(f"Saved camera image to {args.output}")
                else:
                    sys.stdout.buffer.write(image)

            elif args.command == "get-calendars":
                print_json(ha.get_calendars())

            elif args.command == "get-calendar-events":
                print_json(ha.get_calendar_events(args.entity_id, args.start, args.end))

            elif args.command == "get-error-log":
                print(ha.get_error_log())

            elif args.command == "check-config":
                print_json(ha.check_config())

            elif args.command == "handle-intent":
                data = parse_json_arg(args.data, "--data")
                print_json(ha.handle_intent(args.name, data or None))

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        exit(1)


if __name__ == "__main__":
    main()
