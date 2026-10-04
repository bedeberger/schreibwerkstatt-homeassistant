"""Dashboard strategy: serves the JS module and tells it which entity shows which metric.

Entity IDs depend on device names (the users' display names) and the HA language, so the
strategy never guesses them; it asks `schreibwerkstatt/entities` for the mapping
metric + labels → entity_id and builds the dashboard from that.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.loader import async_get_integration

from .const import DOMAIN, GOAL_METRIC
from .coordinator import SchreibwerkstattCoordinator
from .entity import instance_key, user_identifier
from .models import USER_LABELS

STRATEGY_URL = f"/{DOMAIN}/{DOMAIN}-strategy.js"
STRATEGY_FILE = Path(__file__).parent / "frontend" / f"{DOMAIN}-strategy.js"
# Pseudo metric of the "daily goal reached" binary sensor.
GOAL_REACHED = "daily_goal_reached"


async def async_setup_frontend(hass: HomeAssistant) -> None:
    """Register the websocket command and, with a frontend, the strategy module."""
    websocket_api.async_register_command(hass, ws_entities)
    if "frontend" not in hass.config.components or hass.http is None:
        return
    # Imported late: the frontend package is not installed everywhere (tests).
    from homeassistant.components.frontend import add_extra_js_url

    version = (await async_get_integration(hass, DOMAIN)).version
    await hass.http.async_register_static_paths([StaticPathConfig(STRATEGY_URL, str(STRATEGY_FILE), False)])
    add_extra_js_url(hass, f"{STRATEGY_URL}?v={version}")


@callback
def async_dashboard_entities(hass: HomeAssistant) -> list[dict[str, Any]]:
    """Per loaded entry: users and every enabled entity with the metric it shows."""
    return [
        {
            "entry_id": entry.entry_id,
            "title": entry.title,
            "includes_users": entry.runtime_data.data.includes_users,
            "users": _users(hass, entry.runtime_data),
            "entities": _entities(hass, entry.runtime_data),
        }
        for entry in hass.config_entries.async_entries(DOMAIN)
        if entry.state is ConfigEntryState.LOADED
    ]


def _entities(hass: HomeAssistant, coordinator: SchreibwerkstattCoordinator) -> list[dict[str, Any]]:
    """Enabled entities of one entry, keyed by metric, labels and user."""
    registry = er.async_get(hass)
    root = instance_key(coordinator)
    out = []

    def _add(platform: str, unique_id: str, metric: str, labels: dict[str, str], user: str | None) -> None:
        entity_id = registry.async_get_entity_id(platform, DOMAIN, unique_id)
        if entity_id is None or registry.async_get(entity_id).disabled:
            return
        out.append({"entity_id": entity_id, "metric": metric, "labels": labels, "user": user})

    for sample in coordinator.data.samples.values():
        labels = {k: v for k, v in sample.labels.items() if k not in USER_LABELS}
        _add("sensor", f"{root}_{sample.key}", sample.metric.name, labels, sample.user)
        if sample.metric.name == GOAL_METRIC and sample.user:
            _add("binary_sensor", f"{root}_{GOAL_REACHED}_{sample.user}", GOAL_REACHED, {}, sample.user)
    return out


def _users(hass: HomeAssistant, coordinator: SchreibwerkstattCoordinator) -> list[dict[str, Any]]:
    """Users in display order, named like their device (a user rename in HA wins)."""
    registry = dr.async_get(hass)
    out = []
    for email, name in coordinator.data.users.items():
        device = registry.async_get_device(identifiers={user_identifier(coordinator, email)})
        out.append(
            {
                "user": email,
                "name": (device and (device.name_by_user or device.name)) or name,
                "device_id": device and device.id,
            }
        )
    return sorted(out, key=lambda u: u["name"].casefold())


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/entities"})
@callback
def ws_entities(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """Mapping for the dashboard strategy."""
    connection.send_result(msg["id"], {"entries": async_dashboard_entities(hass)})
