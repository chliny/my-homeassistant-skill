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
        verify_ssl: bool = False
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
            raise ValueError("HA_URL not set, please set environment variable or pass url parameter")
        if not self.token:
            raise ValueError("HA_TOKEN not set, please set environment variable or pass token parameter")

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
            "Content-Type": "application/json"
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
        keys = ["http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "all_proxy", "ALL_PROXY"]
        for env_key in keys:
            os.environ.pop(env_key, None)
        return None

    def _request(
        self,
        method: str,
        endpoint: str,
        data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None
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
        self,
        entity_id: str,
        state: str,
        attributes: dict[str, Any] | None = None
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
                "attributes": state["attributes"]
            }
            for state in states
        ]

    # ==================== Service Calls ====================

    def call_service(
        self,
        domain: str,
        service: str,
        entity_id: str | None = None,
        return_response: bool = False,
        **kwargs: Any
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

    # ==================== Events ====================

    def fire_event(
        self,
        event_type: str,
        event_data: dict[str, Any] | None = None
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
        significant_changes_only: bool = False
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
        end_time: str | None = None
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

    def get_camera_image(
        self,
        entity_id: str,
        timestamp: str | None = None
    ) -> bytes:
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
        self,
        entity_id: str,
        start: str,
        end: str
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
            "GET",
            f"/calendars/{entity_id}",
            params={"start": start, "end": end}
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

    def handle_intent(self, name: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
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

    parser = argparse.ArgumentParser(description="Home Assistant REST API client")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Get entity state
    get_entity_parser = subparsers.add_parser("get-entity", help="Get entity state")
    get_entity_parser.add_argument("entity_id", help="Entity ID")

    # List all entities
    subparsers.add_parser("list-entities", help="List all entity ID state and friendly name")

    # List available entities
    subparsers.add_parser("list-available-entities", help="List available entities (exclude unavailable)")

    # Get live context
    subparsers.add_parser("live-context", help="Get live context of all entities")

    # Call service
    call_service_parser = subparsers.add_parser("call-service", help="Call service")
    call_service_parser.add_argument("domain", help="Service domain")
    call_service_parser.add_argument("service", help="Service name")
    call_service_parser.add_argument("--entity-id", help="Entity ID")
    call_service_parser.add_argument("--data", help="Service data in JSON format")

    # Check API
    subparsers.add_parser("check-api", help="Check if API is running")

    # Get configuration
    subparsers.add_parser("get-config", help="Get configuration information")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        with HomeAssistantAPI() as ha:
            if args.command == "get-entity":
                result = ha.get_entity(args.entity_id)
                print(json.dumps(result, indent=2, ensure_ascii=False))

            elif args.command == "list-entities":
                entities = ha.list_entities()
                for entity in entities:
                    print(entity)

            elif args.command == "list-available-entities":
                entities = ha.list_entities(available_only=True)
                for entity in entities:
                    print(entity)

            elif args.command == "live-context":
                context = ha.get_live_context()
                print(json.dumps(context, indent=2, ensure_ascii=False))

            elif args.command == "call-service":
                data = json.loads(args.data) if args.data else {}
                result = ha.call_service(
                    args.domain,
                    args.service,
                    entity_id=args.entity_id,
                    **data
                )
                if result:
                    print(json.dumps(result, indent=2, ensure_ascii=False))

            elif args.command == "check-api":
                result = ha.check_api()
                print(json.dumps(result, indent=2, ensure_ascii=False))

            elif args.command == "get-config":
                result = ha.get_config()
                print(json.dumps(result, indent=2, ensure_ascii=False))

    except Exception as e:
        print(f"Error: {e}", file=__import__("sys").stderr)
        exit(1)


if __name__ == "__main__":
    main()
