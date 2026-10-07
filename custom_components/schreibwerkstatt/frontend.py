"""Dashboard strategy: serves the JS module and tells it which entity shows which metric.

Entity IDs depend on device names (the users' display names) and the HA language, so the
strategy never guesses them; it asks `schreibwerkstatt/entities` for the mapping
metric + labels → entity_id and builds the dashboard from that.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.loader import async_get_integration

from .const import DOMAIN, GOAL_METRIC
from .coordinator import SchreibwerkstattCoordinator
from .entity import instance_key, user_identifier
from .models import USER_LABELS

_LOGGER = logging.getLogger(__name__)

STRATEGY_URL = f"/{DOMAIN}/{DOMAIN}-strategy.js"
STRATEGY_FILE = Path(__file__).parent / "frontend" / f"{DOMAIN}-strategy.js"
# Pseudo metric of the "daily goal reached" binary sensor.
GOAL_REACHED = "daily_goal_reached"


async def async_setup_frontend(hass: HomeAssistant) -> None:
    """Register the websocket command, the static path and a Lovelace resource for the strategy."""
    websocket_api.async_register_command(hass, ws_entities)
    if "frontend" not in hass.config.components or hass.http is None:
        return

    version = (await async_get_integration(hass, DOMAIN)).version
    await hass.http.async_register_static_paths([StaticPathConfig(STRATEGY_URL, str(STRATEGY_FILE), False)])
    strategy_url = f"{STRATEGY_URL}?v={version}"

    # Lovelace resources are awaited before the dashboard renders; add_extra_js_url
    # modules are not (home-assistant/frontend#52570) and race the 5 s
    # strategy-load timeout. In storage mode register the module as a resource so the
    # user does not have to. YAML mode and "not yet initialised" each get a
    # best-effort fallback; the latter retries on home-assistant start-up.
    if await _async_ensure_resource(hass, strategy_url):
        return

    async def _on_started(_event: Any) -> None:
        await _async_ensure_resource(hass, strategy_url)

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _on_started)


async def _async_ensure_resource(hass: HomeAssistant, url: str) -> bool:
    """Make sure the strategy module is registered as a Lovelace resource.

    Returns True once the resource is in place (created, already up to date, or a
    YAML-mode fallback logged). Returns False when Lovelace is not yet initialised
    so the caller can retry on home-assistant start-up.
    """
    # Imported late: the frontend package is not installed everywhere (tests).
    from homeassistant.components.frontend import add_extra_js_url

    lovelace = hass.data.get("lovelace")
    if lovelace is None:
        return False

    # HA 2025.1 stores lovelace as a plain dict, newer releases as a dataclass.
    if isinstance(lovelace, dict):
        resources = lovelace.get("resources")
    else:
        resources = getattr(lovelace, "resources", None)
    if resources is None or not hasattr(resources, "async_create_item"):
        _LOGGER.warning(
            "Lovelace is in YAML mode: to stop the 'Timeout waiting for strategy "
            "element' error when configuring the Schreibwerkstatt dashboard, add "
            "this to configuration.yaml under lovelace.resources:"
            "\n  - url: %s\n    type: module",
            url,
        )
        add_extra_js_url(hass, url)
        return True

    # ResourceStorage.async_items is a @callback (returns a list), not a coroutine.
    items = resources.async_items() or []
    for item in items:
        if str(item.get("url", "")).split("?")[0] != STRATEGY_URL:
            continue
        if item.get("url") == url:
            return True
        await resources.async_update_item(item["id"], {"url": url})
        return True
    await resources.async_create_item({"res_type": "module", "url": url})
    return True


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
