"""Shared fixtures. tests/fixtures/metrics.json is a real /metrics.json answer
(generated from the Schreibwerkstatt collector) and doubles as contract sample."""

from __future__ import annotations

from collections.abc import Generator
import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.schreibwerkstatt.const import DOMAIN
from homeassistant.const import CONF_API_TOKEN, CONF_URL, CONF_VERIFY_SSL

pytest_plugins = "pytest_homeassistant_custom_component"

INSTANCE = "00000000-0000-4000-8000-000000000001"
URL = "https://sw.example.com"
TOKEN = "sw_" + "a" * 64
CLIENT = "custom_components.schreibwerkstatt.api.SchreibwerkstattClient.async_get_metrics"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: Any) -> None:
    """Load custom_components/ in every test."""


@pytest.fixture
def metrics_doc() -> dict[str, Any]:
    return json.loads((Path(__file__).parent / "fixtures" / "metrics.json").read_text())


@pytest.fixture
def mock_metrics(metrics_doc: dict[str, Any]) -> Generator[AsyncMock]:
    with patch(CLIENT, new_callable=AsyncMock, return_value=metrics_doc) as mock:
        yield mock


@pytest.fixture
def config_entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        title="sw.example.com",
        unique_id=INSTANCE,
        data={CONF_URL: URL, CONF_API_TOKEN: TOKEN, CONF_VERIFY_SSL: True},
    )
