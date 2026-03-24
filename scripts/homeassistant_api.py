#!/usr/bin/env python3
"""
Home Assistant REST API Client

Async Python client library for the Home Assistant REST API.
HA_URL and HA_TOKEN are retrieved from environment variables.
"""

import argparse
import asyncio
import ipaddress
import json
import os
import socket
import ssl
import sys
from typing import Any
from urllib.parse import urlparse

import aiohttp


class HomeAssistantAPI:
    """Home Assistant REST API client."""

    def __init__(
        self,
        url: str | None = None,
        token: str | None = None,
        timeout: int = 10,
        verify_ssl: bool = False,
        max_retries: int = 3,
        retry_backoff: float = 1.0,
    ):
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

        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff
        self.session: aiohttp.ClientSession | None = None

        if self._check_internal_url():
            self._unset_proxies()

        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def _is_private_ip(self, ip: str) -> bool:
        try:
            ip_obj = ipaddress.ip_address(ip)
            return ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local
        except ValueError:
            return False

    def _check_internal_url(self) -> bool:
        parsed = urlparse(self.url)
        hostname = parsed.hostname or ""

        if self._is_private_ip(hostname):
            return True

        try:
            ip = socket.gethostbyname(hostname)
            return self._is_private_ip(ip)
        except socket.gaierror:
            return False

    def _unset_proxies(self) -> None:
        for env_key in (
            "http_proxy",
            "https_proxy",
            "HTTP_PROXY",
            "HTTPS_PROXY",
            "all_proxy",
            "ALL_PROXY",
        ):
            os.environ.pop(env_key, None)

    def _build_ssl_context(self) -> ssl.SSLContext | bool:
        if self.verify_ssl:
            return ssl.create_default_context()

        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        return ssl_context

    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            connector = aiohttp.TCPConnector(ssl=self._build_ssl_context())
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self.session = aiohttp.ClientSession(
                headers=self.headers,
                timeout=timeout,
                connector=connector,
                trust_env=True,
            )
        return self.session

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        response_type: str = "json",
    ) -> Any:
        url = f"{self.url}/api{endpoint}"
        session = await self._ensure_session()
        last_error: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                async with session.request(
                    method=method,
                    url=url,
                    json=data,
                    params=params,
                ) as response:
                    if response.status >= 400:
                        error = aiohttp.ClientResponseError(
                            response.request_info,
                            response.history,
                            status=response.status,
                            message=await response.text(),
                            headers=response.headers,
                        )
                        if response.status in {429, 500, 502, 503, 504}:
                            raise error
                        raise error

                    if response_type == "bytes":
                        return await response.read()

                    if response_type == "text":
                        return await response.text()

                    text = await response.text()
                    if not text:
                        return None
                    return json.loads(text)

            except (
                aiohttp.ClientError,
                asyncio.TimeoutError,
                json.JSONDecodeError,
            ) as exc:
                last_error = exc
                is_retryable = (
                    isinstance(exc, asyncio.TimeoutError)
                    or (
                        isinstance(exc, aiohttp.ClientResponseError)
                        and exc.status in {429, 500, 502, 503, 504}
                    )
                    or isinstance(exc, aiohttp.ClientConnectionError)
                )

                if attempt == self.max_retries - 1 or not is_retryable:
                    raise

                await asyncio.sleep(self.retry_backoff * (2**attempt))

        if last_error is not None:
            raise last_error
        return None

    async def check_api(self) -> dict[str, Any]:
        return await self._request("GET", "/")

    async def get_config(self) -> dict[str, Any]:
        return await self._request("GET", "/config")

    async def get_components(self) -> list[str]:
        return await self._request("GET", "/components")

    async def get_events(self) -> list[dict[str, Any]]:
        return await self._request("GET", "/events")

    async def get_services(self) -> list[dict[str, Any]]:
        return await self._request("GET", "/services")

    async def get_states(self) -> list[dict[str, Any]]:
        return await self._request("GET", "/states")

    async def get_entity(self, entity_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/states/{entity_id}")

    async def set_state(
        self, entity_id: str, state: str, attributes: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        data: dict[str, Any] = {"state": state}
        if attributes:
            data["attributes"] = attributes
        return await self._request("POST", f"/states/{entity_id}", data=data)

    async def delete_entity(self, entity_id: str) -> None:
        await self._request("DELETE", f"/states/{entity_id}")

    async def list_entities(self, available_only: bool = False) -> list[str]:
        states = await self.get_states()
        result = []
        for state in states:
            entity_id = state["entity_id"]
            entity_state = state["state"]
            if available_only and entity_state == "unavailable":
                continue

            friendly_name = state.get("attributes", {}).get("friendly_name", "")
            friendly_name = "_".join(friendly_name.strip().split())
            entity_state = "_".join(entity_state.strip().split())
            result.append(f"{entity_id} {entity_state} {friendly_name}")
        return result

    async def get_live_context(self) -> list[dict[str, Any]]:
        states = await self.get_states()
        return [
            {
                "name": state["entity_id"],
                "domain": state["entity_id"].split(".")[0],
                "state": state["state"],
                "attributes": state["attributes"],
            }
            for state in states
        ]

    async def get_entities_by_domain(self, domain: str) -> list[dict[str, Any]]:
        return [
            state
            for state in await self.get_states()
            if state.get("entity_id", "").startswith(f"{domain}.")
        ]

    async def call_service(
        self,
        domain: str,
        service: str,
        entity_id: str | None = None,
        return_response: bool = False,
        **kwargs: Any,
    ) -> Any:
        data: dict[str, Any] = kwargs
        if entity_id:
            data["entity_id"] = entity_id

        endpoint = f"/services/{domain}/{service}"
        params = {"return_response": ""} if return_response else None
        return await self._request("POST", endpoint, data=data, params=params)

    async def get_scenes(self) -> list[dict[str, Any]]:
        return await self.get_entities_by_domain("scene")

    async def activate_scene(
        self, entity_id: str, transition: float | None = None
    ) -> Any:
        data: dict[str, Any] = {}
        if transition is not None:
            data["transition"] = transition
        return await self.call_service("scene", "turn_on", entity_id=entity_id, **data)

    async def apply_scene(
        self, entities: dict[str, Any], transition: float | None = None
    ) -> Any:
        data: dict[str, Any] = {"entities": entities}
        if transition is not None:
            data["transition"] = transition
        return await self.call_service("scene", "apply", **data)

    async def create_scene(
        self,
        scene_id: str,
        entities: dict[str, Any] | None = None,
        snapshot_entities: list[str] | None = None,
    ) -> Any:
        if not entities and not snapshot_entities:
            raise ValueError("scene.create requires --entities or --snapshot-entities")

        data: dict[str, Any] = {"scene_id": scene_id}
        if entities:
            data["entities"] = entities
        if snapshot_entities:
            data["snapshot_entities"] = snapshot_entities
        return await self.call_service("scene", "create", **data)

    async def delete_scene(self, entity_id: str) -> Any:
        return await self.call_service("scene", "delete", entity_id=entity_id)

    async def reload_scenes(self) -> Any:
        return await self.call_service("scene", "reload")

    async def get_automations(self) -> list[dict[str, Any]]:
        return await self.get_entities_by_domain("automation")

    async def trigger_automation(
        self,
        entity_id: str,
        skip_condition: bool = False,
        variables: dict[str, Any] | None = None,
    ) -> Any:
        data: dict[str, Any] = {}
        if skip_condition:
            data["skip_condition"] = True
        if variables:
            data["variables"] = variables
        return await self.call_service(
            "automation", "trigger", entity_id=entity_id, **data
        )

    async def turn_on_automation(self, entity_id: str) -> Any:
        return await self.call_service("automation", "turn_on", entity_id=entity_id)

    async def turn_off_automation(
        self, entity_id: str, stop_actions: bool = False
    ) -> Any:
        data: dict[str, Any] = {}
        if stop_actions:
            data["stop_actions"] = True
        return await self.call_service(
            "automation", "turn_off", entity_id=entity_id, **data
        )

    async def toggle_automation(self, entity_id: str) -> Any:
        return await self.call_service("automation", "toggle", entity_id=entity_id)

    async def reload_automations(self) -> Any:
        return await self.call_service("automation", "reload")

    async def get_todo_lists(self) -> list[dict[str, Any]]:
        return await self.get_entities_by_domain("todo")

    async def get_scripts(self) -> list[dict[str, Any]]:
        return await self.get_entities_by_domain("script")

    async def get_input_booleans(self) -> list[dict[str, Any]]:
        return await self.get_entities_by_domain("input_boolean")

    async def get_input_selects(self) -> list[dict[str, Any]]:
        return await self.get_entities_by_domain("input_select")

    def _validate_todo_due_fields(
        self, due_date: str | None = None, due_datetime: str | None = None
    ) -> None:
        if due_date and due_datetime:
            raise ValueError("Only one of due_date or due_datetime may be provided")

    async def run_script(
        self,
        entity_id: str,
        variables: dict[str, Any] | None = None,
        return_response: bool = False,
    ) -> Any:
        data: dict[str, Any] = {}
        if variables:
            data.update(variables)
        return await self.call_service(
            "script",
            "turn_on",
            entity_id=entity_id,
            return_response=return_response,
            **data,
        )

    async def turn_off_script(self, entity_id: str) -> Any:
        return await self.call_service("script", "turn_off", entity_id=entity_id)

    async def toggle_script(self, entity_id: str) -> Any:
        return await self.call_service("script", "toggle", entity_id=entity_id)

    async def reload_scripts(self) -> Any:
        return await self.call_service("script", "reload")

    async def turn_on_input_boolean(self, entity_id: str) -> Any:
        return await self.call_service("input_boolean", "turn_on", entity_id=entity_id)

    async def turn_off_input_boolean(self, entity_id: str) -> Any:
        return await self.call_service("input_boolean", "turn_off", entity_id=entity_id)

    async def toggle_input_boolean(self, entity_id: str) -> Any:
        return await self.call_service("input_boolean", "toggle", entity_id=entity_id)

    async def reload_input_booleans(self) -> Any:
        return await self.call_service("input_boolean", "reload")

    async def select_input_option(self, entity_id: str, option: str) -> Any:
        return await self.call_service(
            "input_select", "select_option", entity_id=entity_id, option=option
        )

    async def select_next_input_option(self, entity_id: str, cycle: bool = True) -> Any:
        return await self.call_service(
            "input_select", "select_next", entity_id=entity_id, cycle=cycle
        )

    async def select_previous_input_option(
        self, entity_id: str, cycle: bool = True
    ) -> Any:
        return await self.call_service(
            "input_select", "select_previous", entity_id=entity_id, cycle=cycle
        )

    async def set_input_select_options(self, entity_id: str, options: list[str]) -> Any:
        return await self.call_service(
            "input_select", "set_options", entity_id=entity_id, options=options
        )

    async def reload_input_selects(self) -> Any:
        return await self.call_service("input_select", "reload")

    async def get_todo_items(
        self, entity_id: str, status: str | list[str] | None = None
    ) -> Any:
        data: dict[str, Any] = {}
        if status is not None:
            data["status"] = status
        return await self.call_service(
            "todo",
            "get_items",
            entity_id=entity_id,
            return_response=True,
            **data,
        )

    async def add_todo_item(
        self,
        entity_id: str,
        item: str,
        due_date: str | None = None,
        due_datetime: str | None = None,
        description: str | None = None,
    ) -> Any:
        self._validate_todo_due_fields(due_date, due_datetime)
        data: dict[str, Any] = {"item": item}
        if due_date:
            data["due_date"] = due_date
        if due_datetime:
            data["due_datetime"] = due_datetime
        if description:
            data["description"] = description
        return await self.call_service("todo", "add_item", entity_id=entity_id, **data)

    async def update_todo_item(
        self,
        entity_id: str,
        item: str,
        rename: str | None = None,
        status: str | None = None,
        due_date: str | None = None,
        due_datetime: str | None = None,
        description: str | None = None,
    ) -> Any:
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
        return await self.call_service(
            "todo", "update_item", entity_id=entity_id, **data
        )

    async def remove_todo_item(self, entity_id: str, item: str) -> Any:
        return await self.call_service(
            "todo", "remove_item", entity_id=entity_id, item=item
        )

    async def remove_completed_todo_items(self, entity_id: str) -> Any:
        return await self.call_service(
            "todo", "remove_completed_items", entity_id=entity_id
        )

    async def fire_event(
        self, event_type: str, event_data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        return await self._request("POST", f"/events/{event_type}", data=event_data)

    async def get_history(
        self,
        entity_ids: list[str],
        timestamp: str | None = None,
        end_time: str | None = None,
        minimal_response: bool = False,
        no_attributes: bool = False,
        significant_changes_only: bool = False,
    ) -> list[Any]:
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
        return await self._request("GET", endpoint, params=params)

    async def get_logbook(
        self,
        timestamp: str | None = None,
        entity: str | None = None,
        end_time: str | None = None,
    ) -> list[dict[str, Any]]:
        endpoint = f"/logbook/{timestamp}" if timestamp else "/logbook"
        params: dict[str, Any] = {}
        if entity:
            params["entity"] = entity
        if end_time:
            params["end_time"] = end_time
        return await self._request("GET", endpoint, params=params)

    async def render_template(self, template: str) -> str:
        return await self._request(
            "POST", "/template", data={"template": template}, response_type="text"
        )

    async def get_camera_image(
        self, entity_id: str, timestamp: str | None = None
    ) -> bytes:
        params = {"time": timestamp} if timestamp else None
        return await self._request(
            "GET",
            f"/camera_proxy/{entity_id}",
            params=params,
            response_type="bytes",
        )

    async def get_calendars(self) -> list[dict[str, Any]]:
        return await self._request("GET", "/calendars")

    async def get_calendar_events(
        self, entity_id: str, start: str, end: str
    ) -> list[dict[str, Any]]:
        return await self._request(
            "GET", f"/calendars/{entity_id}", params={"start": start, "end": end}
        )

    async def get_error_log(self) -> str:
        return await self._request("GET", "/error_log", response_type="text")

    async def check_config(self) -> dict[str, Any]:
        return await self._request("POST", "/config/core/check_config")

    async def handle_intent(
        self, name: str, data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"name": name}
        if data:
            payload["data"] = data
        return await self._request("POST", "/intent/handle", data=payload)

    async def close(self) -> None:
        if self.session is not None and not self.session.closed:
            await self.session.close()

    async def __aenter__(self) -> "HomeAssistantAPI":
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()


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


def build_parser() -> argparse.ArgumentParser:
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

    get_entity_parser = subparsers.add_parser("get-entity", help="Get entity state")
    get_entity_parser.add_argument("entity_id", help="Entity ID")

    set_state_parser = subparsers.add_parser("set-state", help="Set entity state")
    set_state_parser.add_argument("entity_id", help="Entity ID")
    set_state_parser.add_argument("state", help="State value")
    set_state_parser.add_argument(
        "--attributes", help="State attributes in JSON format"
    )

    delete_entity_parser = subparsers.add_parser(
        "delete-entity", help="Delete entity state"
    )
    delete_entity_parser.add_argument("entity_id", help="Entity ID")

    list_entities_parser = subparsers.add_parser(
        "list-entities", help="List all entity ID state and friendly name"
    )
    list_entities_parser.add_argument(
        "--domain", help="Only list entities from this domain"
    )

    list_available_parser = subparsers.add_parser(
        "list-available-entities", help="List available entities (exclude unavailable)"
    )
    list_available_parser.add_argument(
        "--domain", help="Only list entities from this domain"
    )

    subparsers.add_parser("live-context", help="Get live context of all entities")

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
        "--snapshot-entities", nargs="+", help="Entity IDs to snapshot into the scene"
    )

    delete_scene_parser = subparsers.add_parser(
        "delete-scene", help="Delete a dynamic scene"
    )
    delete_scene_parser.add_argument("entity_id", help="Scene entity ID")
    subparsers.add_parser("reload-scenes", help="Reload scene configuration")

    trigger_automation_parser = subparsers.add_parser(
        "trigger-automation", help="Trigger an automation"
    )
    trigger_automation_parser.add_argument("entity_id", help="Automation entity ID")
    trigger_automation_parser.add_argument(
        "--skip-condition", action="store_true", help="Skip automation condition checks"
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
        "--stop-actions", action="store_true", help="Stop currently running actions"
    )

    toggle_automation_parser = subparsers.add_parser(
        "toggle-automation", help="Toggle automation enabled state"
    )
    toggle_automation_parser.add_argument("entity_id", help="Automation entity ID")
    subparsers.add_parser("reload-automations", help="Reload automation configuration")

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
        "options", nargs="+", help="New option values"
    )
    subparsers.add_parser(
        "reload-input-selects", help="Reload input_select configuration"
    )

    call_service_parser = subparsers.add_parser("call-service", help="Call service")
    call_service_parser.add_argument("domain", help="Service domain")
    call_service_parser.add_argument("service", help="Service name")
    call_service_parser.add_argument("--entity-id", help="Entity ID")
    call_service_parser.add_argument("--data", help="Service data in JSON format")
    call_service_parser.add_argument(
        "--return-response", action="store_true", help="Return service response data"
    )

    fire_event_parser = subparsers.add_parser("fire-event", help="Fire an event")
    fire_event_parser.add_argument("event_type", help="Event type")
    fire_event_parser.add_argument("--data", help="Event data in JSON format")

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

    logbook_parser = subparsers.add_parser("get-logbook", help="Get logbook entries")
    logbook_parser.add_argument("--timestamp", help="Start timestamp")
    logbook_parser.add_argument("--entity", help="Filter by entity ID")
    logbook_parser.add_argument("--end-time", help="End timestamp")

    template_parser = subparsers.add_parser(
        "render-template", help="Render Home Assistant template"
    )
    template_group = template_parser.add_mutually_exclusive_group(required=True)
    template_group.add_argument("template", nargs="?", help="Inline template string")
    template_group.add_argument("--file", help="Read template from file")

    camera_parser = subparsers.add_parser("get-camera-image", help="Fetch camera image")
    camera_parser.add_argument("entity_id", help="Camera entity ID")
    camera_parser.add_argument("--timestamp", help="Image timestamp")
    camera_parser.add_argument("--output", help="Write image to file instead of stdout")

    subparsers.add_parser("get-calendars", help="Get calendar entities")

    calendar_events_parser = subparsers.add_parser(
        "get-calendar-events", help="Get calendar events"
    )
    calendar_events_parser.add_argument("entity_id", help="Calendar entity ID")
    calendar_events_parser.add_argument("start", help="Start time")
    calendar_events_parser.add_argument("end", help="End time")

    subparsers.add_parser("get-error-log", help="Get Home Assistant error log")
    subparsers.add_parser("check-config", help="Check Home Assistant configuration")

    intent_parser = subparsers.add_parser(
        "handle-intent", help="Handle Home Assistant intent"
    )
    intent_parser.add_argument("name", help="Intent name")
    intent_parser.add_argument("--data", help="Intent data in JSON format")

    return parser


async def main_async() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        async with HomeAssistantAPI() as ha:
            if args.command == "check-api":
                print_json(await ha.check_api())
            elif args.command == "get-config":
                print_json(await ha.get_config())
            elif args.command == "get-components":
                print_json(await ha.get_components())
            elif args.command == "get-events":
                print_json(await ha.get_events())
            elif args.command == "get-services":
                print_json(await ha.get_services())
            elif args.command == "get-states":
                print_json(await ha.get_states())
            elif args.command == "get-scenes":
                print_json(await ha.get_scenes())
            elif args.command == "get-automations":
                print_json(await ha.get_automations())
            elif args.command == "get-todo-lists":
                print_json(await ha.get_todo_lists())
            elif args.command == "get-scripts":
                print_json(await ha.get_scripts())
            elif args.command == "get-input-booleans":
                print_json(await ha.get_input_booleans())
            elif args.command == "get-input-selects":
                print_json(await ha.get_input_selects())
            elif args.command == "get-entity":
                print_json(await ha.get_entity(args.entity_id))
            elif args.command == "set-state":
                attributes = parse_json_arg(args.attributes, "--attributes")
                print_json(
                    await ha.set_state(
                        args.entity_id, args.state, attributes=attributes or None
                    )
                )
            elif args.command == "delete-entity":
                await ha.delete_entity(args.entity_id)
                print(f"Deleted {args.entity_id}")
            elif args.command == "list-entities":
                entities = await ha.list_entities()
                for entity in entities:
                    if args.domain and not entity.startswith(f"{args.domain}."):
                        continue
                    print(entity)
            elif args.command == "list-available-entities":
                entities = await ha.list_entities(available_only=True)
                for entity in entities:
                    if args.domain and not entity.startswith(f"{args.domain}."):
                        continue
                    print(entity)
            elif args.command == "live-context":
                print_json(await ha.get_live_context())
            elif args.command == "activate-scene":
                result = await ha.activate_scene(
                    args.entity_id, transition=args.transition
                )
                if result:
                    print_json(result)
            elif args.command == "apply-scene":
                entities = parse_json_arg(args.entities, "--entities")
                result = await ha.apply_scene(entities, transition=args.transition)
                if result:
                    print_json(result)
            elif args.command == "create-scene":
                entities = parse_json_arg(args.entities, "--entities")
                result = await ha.create_scene(
                    args.scene_id,
                    entities=entities or None,
                    snapshot_entities=args.snapshot_entities,
                )
                if result:
                    print_json(result)
            elif args.command == "delete-scene":
                result = await ha.delete_scene(args.entity_id)
                if result:
                    print_json(result)
            elif args.command == "reload-scenes":
                result = await ha.reload_scenes()
                if result:
                    print_json(result)
            elif args.command == "trigger-automation":
                variables = parse_json_arg(args.variables, "--variables")
                result = await ha.trigger_automation(
                    args.entity_id,
                    skip_condition=args.skip_condition,
                    variables=variables or None,
                )
                if result:
                    print_json(result)
            elif args.command == "turn-on-automation":
                result = await ha.turn_on_automation(args.entity_id)
                if result:
                    print_json(result)
            elif args.command == "turn-off-automation":
                result = await ha.turn_off_automation(
                    args.entity_id, stop_actions=args.stop_actions
                )
                if result:
                    print_json(result)
            elif args.command == "toggle-automation":
                result = await ha.toggle_automation(args.entity_id)
                if result:
                    print_json(result)
            elif args.command == "reload-automations":
                result = await ha.reload_automations()
                if result:
                    print_json(result)
            elif args.command == "get-todo-items":
                statuses: str | list[str] | None = args.status
                if statuses and len(statuses) == 1:
                    statuses = statuses[0]
                print_json(await ha.get_todo_items(args.entity_id, status=statuses))
            elif args.command == "add-todo-item":
                result = await ha.add_todo_item(
                    args.entity_id,
                    args.item,
                    due_date=args.due_date,
                    due_datetime=args.due_datetime,
                    description=args.description,
                )
                if result:
                    print_json(result)
            elif args.command == "update-todo-item":
                result = await ha.update_todo_item(
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
                result = await ha.remove_todo_item(args.entity_id, args.item)
                if result:
                    print_json(result)
            elif args.command == "clear-completed-todo":
                result = await ha.remove_completed_todo_items(args.entity_id)
                if result:
                    print_json(result)
            elif args.command == "run-script":
                variables = parse_json_arg(args.variables, "--variables")
                result = await ha.run_script(
                    args.entity_id,
                    variables=variables or None,
                    return_response=args.return_response,
                )
                if result:
                    print_json(result)
            elif args.command == "turn-off-script":
                result = await ha.turn_off_script(args.entity_id)
                if result:
                    print_json(result)
            elif args.command == "toggle-script":
                result = await ha.toggle_script(args.entity_id)
                if result:
                    print_json(result)
            elif args.command == "reload-scripts":
                result = await ha.reload_scripts()
                if result:
                    print_json(result)
            elif args.command == "turn-on-input-boolean":
                result = await ha.turn_on_input_boolean(args.entity_id)
                if result:
                    print_json(result)
            elif args.command == "turn-off-input-boolean":
                result = await ha.turn_off_input_boolean(args.entity_id)
                if result:
                    print_json(result)
            elif args.command == "toggle-input-boolean":
                result = await ha.toggle_input_boolean(args.entity_id)
                if result:
                    print_json(result)
            elif args.command == "reload-input-booleans":
                result = await ha.reload_input_booleans()
                if result:
                    print_json(result)
            elif args.command == "select-input-option":
                result = await ha.select_input_option(args.entity_id, args.option)
                if result:
                    print_json(result)
            elif args.command == "select-next-input-option":
                result = await ha.select_next_input_option(
                    args.entity_id, cycle=not args.no_cycle
                )
                if result:
                    print_json(result)
            elif args.command == "select-previous-input-option":
                result = await ha.select_previous_input_option(
                    args.entity_id, cycle=not args.no_cycle
                )
                if result:
                    print_json(result)
            elif args.command == "set-input-select-options":
                result = await ha.set_input_select_options(args.entity_id, args.options)
                if result:
                    print_json(result)
            elif args.command == "reload-input-selects":
                result = await ha.reload_input_selects()
                if result:
                    print_json(result)
            elif args.command == "call-service":
                data = parse_json_arg(args.data, "--data")
                result = await ha.call_service(
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
                print_json(await ha.fire_event(args.event_type, data or None))
            elif args.command == "get-history":
                print_json(
                    await ha.get_history(
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
                    await ha.get_logbook(
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
                print(await ha.render_template(template))
            elif args.command == "get-camera-image":
                image = await ha.get_camera_image(
                    args.entity_id, timestamp=args.timestamp
                )
                if args.output:
                    with open(args.output, "wb") as file_handle:
                        file_handle.write(image)
                    print(f"Saved camera image to {args.output}")
                else:
                    sys.stdout.buffer.write(image)
            elif args.command == "get-calendars":
                print_json(await ha.get_calendars())
            elif args.command == "get-calendar-events":
                print_json(
                    await ha.get_calendar_events(args.entity_id, args.start, args.end)
                )
            elif args.command == "get-error-log":
                print(await ha.get_error_log())
            elif args.command == "check-config":
                print_json(await ha.check_config())
            elif args.command == "handle-intent":
                data = parse_json_arg(args.data, "--data")
                print_json(await ha.handle_intent(args.name, data or None))
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
