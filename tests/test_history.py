"""Back-fill of long-term statistics from /metrics/history.json."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

import pytest
from pytest_homeassistant_custom_component.components.recorder.common import async_wait_recording_done

from custom_components.schreibwerkstatt.const import DOMAIN
from custom_components.schreibwerkstatt.history import _rows, async_import_history
from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.statistics import statistics_during_period
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .conftest import INSTANCE


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(recorder_mock: Any, enable_custom_integrations: Any) -> None:
    """The recorder has to come up before hass: it overrides the conftest fixture."""


HISTORY = "custom_components.schreibwerkstatt.api.SchreibwerkstattClient.async_get_history"
ZURICH = ZoneInfo("Europe/Zurich")
ANNA = {"user": "anna@example.com", "user_name": "Anna"}
DAYS = ["2026-09-01", "2026-09-02", "2026-09-03"]


def _series(
    name: str, values: list[float], labels: dict[str, str] | None = None, days=DAYS
) -> dict[str, Any]:
    return {"name": name, "labels": labels or {}, "points": [list(p) for p in zip(days, values, strict=True)]}


HISTORY_DOC = {
    "schema": 1,
    "timezone": "Europe/Zurich",
    "today": "2026-10-04",
    "includes_users": True,
    "series": [
        _series("sw_chars", [6000, 6600, 7200]),
        _series("sw_books_written", [1, 1, 2]),
        _series("sw_chars_today", [600, 600], days=DAYS[1:]),
        _series("sw_writing_seconds_today", [1800, 300], days=DAYS[1:]),
        _series("sw_user_chars", [6000, 6600, 7200], ANNA),
        _series("sw_unknown_metric", [1, 2, 3]),
    ],
}


def _id(hass: HomeAssistant, key: str) -> str:
    entity_id = er.async_get(hass).async_get_entity_id("sensor", DOMAIN, f"{INSTANCE}_{key}")
    assert entity_id, key
    return entity_id


async def _daily(hass: HomeAssistant, entity_id: str, stat: str) -> dict[str, float]:
    rows = await get_instance(hass).async_add_executor_job(
        statistics_during_period,
        hass,
        datetime(2026, 8, 1, tzinfo=UTC),
        datetime(2026, 9, 10, tzinfo=UTC),
        {entity_id},
        "day",
        {},
        {stat},
    )
    return {
        datetime.fromtimestamp(r["start"], UTC).astimezone(ZURICH).date().isoformat(): r[stat]
        for r in rows.get(entity_id, [])
    }


async def test_history_back_fill(
    recorder_mock: Any, hass: HomeAssistant, mock_metrics: AsyncMock, config_entry
) -> None:
    with patch(HISTORY, new_callable=AsyncMock, return_value=HISTORY_DOC) as history:
        config_entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done(wait_background_tasks=True)
        await async_wait_recording_done(hass)
    history.assert_awaited_once()

    assert await _daily(hass, _id(hass, "sw_chars"), "max") == dict(
        zip(DAYS, [6000, 6600, 7200], strict=True)
    )
    # Net per day: each day's change is its value.
    assert await _daily(hass, _id(hass, "sw_chars_today"), "change") == {DAYS[1]: 600, DAYS[2]: 600}
    # Seconds on the wire, minutes on the sensor.
    assert await _daily(hass, _id(hass, "sw_writing_seconds_today"), "change") == {DAYS[1]: 30, DAYS[2]: 5}
    # Derived day by day by the live rules.
    assert await _daily(hass, _id(hass, "sw_chars_per_book"), "mean") == dict(
        zip(DAYS, [6000, 6600, 3600], strict=True)
    )
    assert await _daily(hass, _id(hass, "sw_chars_per_author"), "mean") == dict(
        zip(DAYS, [6000, 6600, 7200], strict=True)
    )
    # 5 minutes of writing on the third day: below the threshold, no pace.
    assert await _daily(hass, _id(hass, "sw_chars_per_hour"), "mean") == {DAYS[1]: 1200}

    # A second run (next start) adds nothing: everything is before the first row now.
    before = await _daily(hass, _id(hass, "sw_chars_today"), "sum")
    with patch(HISTORY, new_callable=AsyncMock, return_value=HISTORY_DOC):
        await async_import_history(hass, config_entry.runtime_data)
    await async_wait_recording_done(hass)
    assert await _daily(hass, _id(hass, "sw_chars_today"), "sum") == before


async def test_old_server_without_history(
    recorder_mock: Any, hass: HomeAssistant, mock_metrics: AsyncMock, config_entry
) -> None:
    from custom_components.schreibwerkstatt.api import SchreibwerkstattNotSupportedError

    with patch(HISTORY, new_callable=AsyncMock, side_effect=SchreibwerkstattNotSupportedError("404")):
        config_entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done(wait_background_tasks=True)
    assert await _daily(hass, _id(hass, "sw_chars"), "max") == {}


def test_sums_end_where_recorded_statistics_begin() -> None:
    points = {date(2026, 9, 1): 100.0, date(2026, 9, 2): 50.0, date(2026, 9, 3): 70.0}
    cutoff = datetime(2026, 9, 3, 8, tzinfo=UTC)  # recorder started on the third
    rows = _rows(
        points, ZURICH, cutoff=cutoff, convert=lambda v: v, with_sum=True, daily_reset=True, end_sum=10.0
    )
    assert [r["state"] for r in rows] == [100, 50]
    assert [r["sum"] for r in rows] == [-40, 10]  # ends at the recorded sum
    assert rows[0]["start"] == datetime(2026, 9, 1, 21, tzinfo=UTC)  # 23:00 in Zurich (CEST)
    assert rows[0]["last_reset"] == datetime(2026, 8, 31, 22, tzinfo=UTC)
