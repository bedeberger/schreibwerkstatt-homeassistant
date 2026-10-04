"""Data source of the dashboard strategy."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

from custom_components.schreibwerkstatt.const import DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er

from .conftest import INSTANCE


async def _entities(hass: HomeAssistant, hass_ws_client: Any, config_entry) -> dict[str, Any]:
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": f"{DOMAIN}/entities"})
    msg = await client.receive_json()
    assert msg["success"], msg
    (entry,) = msg["result"]["entries"]
    return entry


def _find(entry: dict[str, Any], metric: str, user: str | None = None, **labels: str) -> str | None:
    for e in entry["entities"]:
        if e["metric"] == metric and e["user"] == user and e["labels"] == labels:
            return e["entity_id"]
    return None


async def test_entities_by_metric_and_user(
    hass: HomeAssistant, hass_ws_client: Any, mock_metrics: AsyncMock, config_entry
) -> None:
    entry = await _entities(hass, hass_ws_client, config_entry)
    assert entry["includes_users"] is True
    assert [u["name"] for u in entry["users"]] == ["Anna", "Ben"]

    # Per-user entities carry the e-mail, not the name-derived entity ID, as key.
    writing = _find(entry, "sw_user_writing_seconds_today", "anna@example.com")
    assert float(hass.states.get(writing).state) == 30
    assert _find(entry, "sw_user_daily_goal_percent", "anna@example.com")
    assert _find(entry, "daily_goal_reached", "anna@example.com").startswith("binary_sensor.")
    assert _find(entry, "sw_user_daily_goal_percent", "ben@example.com") is None

    assert _find(entry, "sw_jobs_ended_24h", status="error")
    assert _find(entry, "sw_tokens_in_total", model="claude-sonnet-4-6", provider="claude")
    # Disabled by default → not offered; device info only → no entity.
    assert _find(entry, "sw_cache_read_tokens_total", model="claude-sonnet-4-6", provider="claude") is None
    assert not any(e["metric"] == "sw_build_info" for e in entry["entities"])


async def test_renamed_user_device_and_entity(
    hass: HomeAssistant, hass_ws_client: Any, mock_metrics: AsyncMock, config_entry
) -> None:
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    devices = dr.async_get(hass)
    anna = devices.async_get_device(identifiers={(DOMAIN, f"{INSTANCE}_user_anna@example.com")})
    devices.async_update_device(anna.id, name_by_user="Zora")
    registry = er.async_get(hass)
    old = registry.async_get_entity_id(
        "sensor", DOMAIN, f"{INSTANCE}_sw_user_writing_seconds_today|user=anna@example.com"
    )
    registry.async_update_entity(old, new_entity_id="sensor.zora_minutes")

    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": f"{DOMAIN}/entities"})
    (entry,) = (await client.receive_json())["result"]["entries"]
    assert [u["name"] for u in entry["users"]] == ["Ben", "Zora"]
    assert _find(entry, "sw_user_writing_seconds_today", "anna@example.com") == "sensor.zora_minutes"
