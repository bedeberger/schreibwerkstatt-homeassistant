"""Entities built from the metrics description."""

from __future__ import annotations

import copy
from typing import Any
from unittest.mock import AsyncMock

from custom_components.schreibwerkstatt.api import SchreibwerkstattAuthError
from custom_components.schreibwerkstatt.const import DOMAIN
from homeassistant.config_entries import SOURCE_REAUTH, ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er

from .conftest import INSTANCE


async def _setup(hass: HomeAssistant, entry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


def _entity_id(hass: HomeAssistant, platform: str, key: str) -> str:
    entity_id = er.async_get(hass).async_get_entity_id(platform, DOMAIN, f"{INSTANCE}_{key}")
    assert entity_id, key
    return entity_id


ANNA = "user=anna@example.com|user_name=Anna"


async def test_sensors_follow_the_description(
    hass: HomeAssistant, mock_metrics: AsyncMock, config_entry
) -> None:
    await _setup(hass, config_entry)

    month = hass.states.get(_entity_id(hass, "sensor", "sw_cost_usd_month"))
    assert float(month.state) == 0.42
    assert month.attributes["unit_of_measurement"] == "USD"
    assert month.attributes["device_class"] == "monetary"
    assert month.attributes["state_class"] == "total"
    assert month.attributes["last_reset"].endswith(("+01:00", "+02:00"))  # Europe/Zurich midnight

    writing = hass.states.get(_entity_id(hass, "sensor", f"sw_user_writing_seconds_today|{ANNA}"))
    assert float(writing.state) == 30  # 1800 s shown in minutes
    assert writing.attributes["unit_of_measurement"] == "min"

    seen = hass.states.get(_entity_id(hass, "sensor", f"sw_user_last_seen_timestamp_seconds|{ANNA}"))
    assert seen.state == "2026-10-04T08:00:00+00:00"

    users = hass.states.get(_entity_id(hass, "sensor", "sw_users|status=active"))
    assert users.state == "2"
    assert users.name.endswith("(active)")


async def test_devices(hass: HomeAssistant, mock_metrics: AsyncMock, config_entry) -> None:
    await _setup(hass, config_entry)
    devices = dr.async_get(hass)
    main = devices.async_get_device(identifiers={(DOMAIN, INSTANCE)})
    assert main.sw_version == "4.16.0"
    assert main.configuration_url == "https://sw.example.com"
    anna = devices.async_get_device(identifiers={(DOMAIN, f"{INSTANCE}_user_anna@example.com")})
    assert anna.name == "Anna"
    assert anna.via_device_id == main.id
    ai = devices.async_get_device(identifiers={(DOMAIN, f"{INSTANCE}_ai")})
    assert ai.name == "Schreibwerkstatt AI"
    # sw_build_info is device info, not an entity.
    assert (
        er.async_get(hass).async_get_entity_id("sensor", DOMAIN, f"{INSTANCE}_sw_build_info|version=4.16.0")
        is None
    )


async def test_disabled_and_diagnostic_defaults(
    hass: HomeAssistant, mock_metrics: AsyncMock, config_entry
) -> None:
    await _setup(hass, config_entry)
    registry = er.async_get(hass)
    # Label-heavy breakdowns are off by default.
    finished = registry.async_get(
        _entity_id(hass, "sensor", "sw_cache_read_tokens_total|model=claude-sonnet-4-6|provider=claude")
    )
    assert finished.disabled_by is er.RegistryEntryDisabler.INTEGRATION
    uptime = registry.async_get(_entity_id(hass, "sensor", "sw_process_uptime_seconds"))
    assert uptime.entity_category == "diagnostic"


async def test_daily_goal_binary_sensor(hass: HomeAssistant, mock_metrics: AsyncMock, config_entry) -> None:
    await _setup(hass, config_entry)
    goal = hass.states.get(_entity_id(hass, "binary_sensor", "daily_goal_reached_anna@example.com"))
    assert goal.state == "on"  # 30 of 30 minutes
    # Ben has no daily goal → no goal sensor.
    assert (
        er.async_get(hass).async_get_entity_id(
            "binary_sensor", DOMAIN, f"{INSTANCE}_daily_goal_reached_ben@example.com"
        )
        is None
    )


async def test_new_samples_appear_and_missing_become_unavailable(
    hass: HomeAssistant, mock_metrics: AsyncMock, metrics_doc: dict[str, Any], config_entry
) -> None:
    await _setup(hass, config_entry)
    doc = copy.deepcopy(metrics_doc)
    for metric in doc["metrics"]:
        if metric["name"] == "sw_user_books":
            metric["samples"].append(
                {"labels": {"user": "cleo@example.com", "user_name": "Cleo"}, "value": 3}
            )
        if metric["name"] == "sw_cost_usd_today":
            metric["samples"] = []
    mock_metrics.return_value = doc
    await config_entry.runtime_data.async_refresh()
    await hass.async_block_till_done()

    cleo = hass.states.get(_entity_id(hass, "sensor", "sw_user_books|user=cleo@example.com|user_name=Cleo"))
    assert cleo.state == "3"
    assert hass.states.get(_entity_id(hass, "sensor", "sw_cost_usd_today")).state == "unavailable"


async def test_revoked_token_starts_reauth(
    hass: HomeAssistant, mock_metrics: AsyncMock, config_entry
) -> None:
    await _setup(hass, config_entry)
    mock_metrics.side_effect = SchreibwerkstattAuthError("401")
    await config_entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    flows = hass.config_entries.flow.async_progress()
    assert any(f["context"]["source"] == SOURCE_REAUTH for f in flows)


async def test_unload(hass: HomeAssistant, mock_metrics: AsyncMock, config_entry) -> None:
    await _setup(hass, config_entry)
    assert await hass.config_entries.async_unload(config_entry.entry_id)
    assert config_entry.state is ConfigEntryState.NOT_LOADED
