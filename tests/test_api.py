"""HTTP client against a fake server."""

from __future__ import annotations

import pytest
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.schreibwerkstatt.api import (
    SchreibwerkstattAuthError,
    SchreibwerkstattClient,
    SchreibwerkstattConnectionError,
    SchreibwerkstattNotSupportedError,
    SchreibwerkstattSchemaError,
    normalize_url,
)
from homeassistant.core import HomeAssistant

from .conftest import TOKEN, URL


def test_normalize_url() -> None:
    assert normalize_url(" https://x.test/metrics.json/ ") == "https://x.test"
    assert normalize_url("https://x.test/metrics") == "https://x.test"
    assert normalize_url("https://x.test/sub/") == "https://x.test/sub"


async def test_fetch_sends_bearer(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, metrics_doc
) -> None:
    aioclient_mock.get(f"{URL}/metrics.json", json=metrics_doc)
    session = aioclient_mock.create_session(hass.loop)
    try:
        doc = await SchreibwerkstattClient(session, URL, TOKEN).async_get_metrics()
    finally:
        await session.close()
    assert doc["schema"] == 1
    assert aioclient_mock.mock_calls[0][3]["Authorization"] == f"Bearer {TOKEN}"


@pytest.mark.parametrize(
    ("status", "body", "error"),
    [
        (401, {"error_code": "INVALID_TOKEN"}, SchreibwerkstattAuthError),
        (403, {"error_code": "INSUFFICIENT_SCOPE"}, SchreibwerkstattAuthError),
        (404, {}, SchreibwerkstattNotSupportedError),
        (500, {}, SchreibwerkstattConnectionError),
        (200, {"schema": 2, "metrics": []}, SchreibwerkstattSchemaError),
        (200, {"schema": 1}, SchreibwerkstattSchemaError),
    ],
)
async def test_fetch_errors(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, status: int, body: dict, error: type
) -> None:
    aioclient_mock.get(f"{URL}/metrics.json", status=status, json=body)
    session = aioclient_mock.create_session(hass.loop)
    try:
        with pytest.raises(error):
            await SchreibwerkstattClient(session, URL, TOKEN).async_get_metrics()
    finally:
        await session.close()
