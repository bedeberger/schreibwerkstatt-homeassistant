"""Config, reauth and options flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from custom_components.schreibwerkstatt.api import (
    SchreibwerkstattAuthError,
    SchreibwerkstattConnectionError,
    SchreibwerkstattNotSupportedError,
    SchreibwerkstattSchemaError,
)
from custom_components.schreibwerkstatt.const import DOMAIN
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_API_TOKEN, CONF_SCAN_INTERVAL, CONF_URL, CONF_VERIFY_SSL
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from .conftest import CLIENT, INSTANCE, TOKEN, URL


async def test_user_flow_creates_entry(hass: HomeAssistant, mock_metrics: AsyncMock) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        # A pasted endpoint URL and stray whitespace are normalised away.
        {CONF_URL: f"{URL}/metrics.json/", CONF_API_TOKEN: f" {TOKEN} ", CONF_VERIFY_SSL: False},
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "sw.example.com"
    assert result["data"] == {CONF_URL: URL, CONF_API_TOKEN: TOKEN, CONF_VERIFY_SSL: False}
    assert result["result"].unique_id == INSTANCE


@pytest.mark.parametrize(
    ("error", "key"),
    [
        (SchreibwerkstattAuthError("401"), "invalid_auth"),
        (SchreibwerkstattConnectionError("down"), "cannot_connect"),
        (SchreibwerkstattNotSupportedError("404"), "not_supported"),
        (SchreibwerkstattSchemaError("schema 2"), "unsupported_schema"),
        (RuntimeError("boom"), "unknown"),
    ],
)
async def test_user_flow_errors(hass: HomeAssistant, error: Exception, key: str) -> None:
    with patch(CLIENT, new_callable=AsyncMock, side_effect=error):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_URL: URL, CONF_API_TOKEN: TOKEN}
        )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": key}


async def test_same_instance_aborts_and_updates_url(
    hass: HomeAssistant, mock_metrics: AsyncMock, config_entry
) -> None:
    config_entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_URL: "https://new-host.example.com", CONF_API_TOKEN: TOKEN}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert config_entry.data[CONF_URL] == "https://new-host.example.com"


async def test_reauth_replaces_token(hass: HomeAssistant, mock_metrics: AsyncMock, config_entry) -> None:
    config_entry.add_to_hass(hass)
    result = await config_entry.start_reauth_flow(hass)
    assert result["step_id"] == "reauth_confirm"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_API_TOKEN: "sw_" + "b" * 64}
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert config_entry.data[CONF_API_TOKEN] == "sw_" + "b" * 64


async def test_options_scan_interval(hass: HomeAssistant, mock_metrics: AsyncMock, config_entry) -> None:
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(result["flow_id"], {CONF_SCAN_INTERVAL: 120})
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert config_entry.options == {CONF_SCAN_INTERVAL: 120}
    assert config_entry.runtime_data.update_interval.total_seconds() == 120
