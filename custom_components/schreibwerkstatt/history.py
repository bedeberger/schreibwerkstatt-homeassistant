"""Back-fill long-term statistics from the server's daily series.

Without this every chart starts on the day the integration was set up, although
the server keeps a snapshot of every book every evening. /metrics/history.json
returns those days under the names and labels of /metrics.json; each series
goes into the statistics of the sensor that shows the metric live.

Only days before the sensor's first recorded statistic are written, so what the
recorder collected itself is never overwritten and a second run (every start)
writes nothing. One row per day at 23:00 local, when the server takes its
snapshot: a line or bar per day, which is what the charts ask for.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, date, datetime, time, timedelta
import logging
from typing import Any

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.models import StatisticData, StatisticMetaData
from homeassistant.components.recorder.statistics import async_import_statistics, statistics_during_period
from homeassistant.const import ATTR_UNIT_OF_MEASUREMENT
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util.unit_conversion import DurationConverter

from .api import SchreibwerkstattError, SchreibwerkstattNotSupportedError
from .const import DOMAIN
from .coordinator import SchreibwerkstattCoordinator
from .entity import instance_key
from .models import derive, sample_key
from .sensor import zone

_LOGGER = logging.getLogger(__name__)

_EPOCH = datetime(2000, 1, 1, tzinfo=UTC)
_SUM_CLASSES = ("total", "total_increasing")

# sample key → (labels, {day: value})
type Series = dict[str, tuple[dict[str, str], dict[date, float]]]


async def async_import_history(hass: HomeAssistant, coordinator: SchreibwerkstattCoordinator) -> None:
    """Fetch the daily series once and write what the recorder does not have yet."""
    if "recorder" not in hass.config.components:
        return
    recorder = get_instance(hass)
    if not await recorder.async_db_ready:
        return
    try:
        doc = await coordinator.client.async_get_history()
    except SchreibwerkstattNotSupportedError:
        _LOGGER.debug("Server has no /metrics/history.json, no history to import")
        return
    except SchreibwerkstattError as err:
        _LOGGER.warning("History not imported: %s", err)
        return

    tz = zone(doc.get("timezone") or coordinator.data.timezone)
    series = _parse(doc)
    _add_derived(series)
    registry = er.async_get(hass)
    root = instance_key(coordinator)
    imported = []
    for key, (_labels, points) in series.items():
        sample = coordinator.data.samples.get(key)
        entity_id = registry.async_get_entity_id("sensor", DOMAIN, f"{root}_{key}")
        if sample is None or entity_id is None or registry.async_get(entity_id).disabled:
            continue
        metric = sample.metric
        with_sum = metric.state_class in _SUM_CLASSES
        if not with_sum and metric.state_class != "measurement":
            continue
        state = hass.states.get(entity_id)
        unit = state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) if state else None
        convert = _converter(metric.device_class, metric.unit, unit)
        if convert is None:
            continue

        first = await recorder.async_add_executor_job(_first_row, hass, entity_id, with_sum)
        rows = _rows(
            points,
            tz,
            cutoff=first[0] if first else None,
            convert=convert,
            with_sum=with_sum,
            daily_reset=metric.reset == "day",
            end_sum=first[1] if first else None,
        )
        if rows:
            async_import_statistics(hass, _metadata(entity_id, unit, with_sum=with_sum), rows)
            imported.append(entity_id)
    if imported:
        _LOGGER.info("Imported history for %d sensors: %s", len(imported), ", ".join(imported))


def _parse(doc: dict[str, Any]) -> Series:
    series: Series = {}
    for s in doc.get("series", []):
        try:
            labels = {str(k): str(v) for k, v in (s.get("labels") or {}).items()}
            points = {date.fromisoformat(d): float(v) for d, v in s.get("points", [])}
        except (TypeError, ValueError):
            continue
        series[sample_key(s["name"], labels)] = (labels, points)
    return series


def _add_derived(series: Series) -> None:
    """The integration's own averages and pace, day by day by the same rules as live."""
    days = sorted({d for _, points in series.values() for d in points})
    for day in days:
        values = {key: (labels, points[day]) for key, (labels, points) in series.items() if day in points}
        for metric, labels, value in derive(values):
            key = sample_key(metric.name, labels)
            series.setdefault(key, (labels, {}))[1][day] = value


type Convert = Callable[[float], float]


def _converter(device_class: str | None, server_unit: str | None, unit: str | None) -> Convert | None:
    """Server value → value in the unit the sensor shows (durations: seconds → minutes)."""
    if device_class != "duration":
        return lambda v: v
    if unit is None:
        return None
    return lambda v: DurationConverter.convert(v, server_unit or "s", unit)


def _first_row(
    hass: HomeAssistant, statistic_id: str, with_sum: bool
) -> tuple[datetime, float | None] | None:
    """Start (and sum) of the first hourly statistic; for sums the first row that has one.

    Runs in the recorder's executor. Months first, so a sensor with years of history
    does not load every hourly row.
    """
    types: set[Any] = {"sum"} if with_sum else {"max"}
    months = statistics_during_period(hass, _EPOCH, None, {statistic_id}, "month", None, types)
    for month in months.get(statistic_id, []):
        if with_sum and month.get("sum") is None:
            continue
        start = datetime.fromtimestamp(month["start"], UTC)
        hours = statistics_during_period(
            hass, start, start + timedelta(days=32), {statistic_id}, "hour", None, types
        )
        for row in hours.get(statistic_id, []):
            if not with_sum or row.get("sum") is not None:
                return datetime.fromtimestamp(row["start"], UTC), row.get("sum")
    return None


def _at(day: date, hour: int, tz: Any) -> datetime:
    # Whole UTC hours: statistics rows must start on one, also in half-hour time zones.
    return datetime.combine(day, time(hour), tz).astimezone(UTC).replace(minute=0, second=0, microsecond=0)


def _rows(
    points: dict[date, float],
    tz: Any,
    *,
    cutoff: datetime | None,
    convert: Convert,
    with_sum: bool,
    daily_reset: bool,
    end_sum: float | None,
) -> list[StatisticData]:
    """One row per day before `cutoff`.

    Sums: every series with a sum restarts daily, so a day's change is its value.
    The running sum ends where the recorded statistics begin (`end_sum`), so the
    first recorded day does not show the whole past as one jump.
    """
    rows: list[StatisticData] = []
    for day in sorted(points):
        start = _at(day, 23, tz)
        if cutoff is not None and start >= cutoff:
            continue
        value = convert(points[day])
        if with_sum:
            rows.append(
                StatisticData(start=start, state=value, last_reset=_at(day, 0, tz) if daily_reset else None)
            )
        else:
            rows.append(StatisticData(start=start, mean=value, min=value, max=value))
    if with_sum:
        total = sum(row["state"] for row in rows)
        running = (end_sum - total) if end_sum is not None else 0.0
        for row in rows:
            running += row["state"]
            row["sum"] = running
    return rows


def _metadata(statistic_id: str, unit: str | None, *, with_sum: bool) -> StatisticMetaData:
    """Metadata as the recorder writes it for the sensor, across HA versions."""
    meta: dict[str, Any] = {
        "has_mean": not with_sum,
        "has_sum": with_sum,
        "name": None,
        "source": "recorder",
        "statistic_id": statistic_id,
        "unit_of_measurement": unit,
    }
    fields = StatisticMetaData.__annotations__
    if "mean_type" in fields:  # HA 2025.4+: mean_type replaces has_mean
        from homeassistant.components.recorder.models import StatisticMeanType  # noqa: PLC0415

        meta["mean_type"] = StatisticMeanType.NONE if with_sum else StatisticMeanType.ARITHMETIC
        if "has_mean" not in fields:
            del meta["has_mean"]
    if "unit_class" in fields:  # HA 2025.10+
        meta["unit_class"] = "duration" if unit in DurationConverter.VALID_UNITS else None
    return StatisticMetaData(**meta)  # type: ignore[typeddict-item]
