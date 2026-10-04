"""Sensors: one generic entity per metric sample of /metrics.json."""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, UnitOfInformation, UnitOfTime
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import SchreibwerkstattConfigEntry, SchreibwerkstattCoordinator
from .entity import SchreibwerkstattEntity, instance_key, ui_lang
from .models import Sample

# Calendar month on the billing side is cut in UTC (Anthropic cost report).
UTC_RESET_METRICS = {"sw_billed_usd_month"}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SchreibwerkstattConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create sensors now and for every sample that shows up later."""
    coordinator = entry.runtime_data
    known: set[str] = set()

    @callback
    def _add_new() -> None:
        new = []
        for key, sample in coordinator.data.samples.items():
            if key in known or not sample.metric.entity:
                continue
            known.add(key)
            new.append(SchreibwerkstattSensor(coordinator, sample))
        if new:
            async_add_entities(new)

    _add_new()
    entry.async_on_unload(coordinator.async_add_listener(_add_new))


def _enum[T](cls: type[T], value: str | None) -> T | None:
    if not value:
        return None
    try:
        return cls(value)  # type: ignore[call-arg]
    except ValueError:
        return None


class SchreibwerkstattSensor(SchreibwerkstattEntity, SensorEntity):
    """A metric sample; all presentation comes from the server description."""

    def __init__(self, coordinator: SchreibwerkstattCoordinator, sample: Sample) -> None:
        super().__init__(coordinator, sample)
        metric = sample.metric
        self._attr_unique_id = f"{instance_key(coordinator)}_{sample.key}"
        name = metric.title_for(ui_lang(coordinator))
        if sample.name_labels:
            name = f"{name} ({' · '.join(sample.name_labels)})"
        self._attr_name = name
        self._attr_icon = metric.icon
        self._attr_entity_registry_enabled_default = metric.enabled_default
        if metric.diagnostic:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

        device_class = _enum(SensorDeviceClass, metric.device_class)
        self._attr_device_class = device_class
        if device_class == SensorDeviceClass.TIMESTAMP:
            return
        self._attr_native_unit_of_measurement = metric.unit
        self._attr_state_class = _enum(SensorStateClass, metric.state_class)
        if device_class == SensorDeviceClass.DURATION:
            # Seconds on the wire; minutes read better for daily times, hours for uptime.
            self._attr_suggested_unit_of_measurement = (
                UnitOfTime.MINUTES if metric.reset else UnitOfTime.HOURS
            )
            self._attr_suggested_display_precision = 0 if metric.reset else 1
        elif device_class == SensorDeviceClass.DATA_SIZE:
            self._attr_suggested_unit_of_measurement = UnitOfInformation.MEBIBYTES
            self._attr_suggested_display_precision = 1
        elif device_class == SensorDeviceClass.MONETARY:
            self._attr_suggested_display_precision = 2

    @property
    def native_value(self) -> float | int | datetime | None:
        sample = self.sample
        if sample is None:
            return None
        if self._attr_device_class == SensorDeviceClass.TIMESTAMP:
            return datetime.fromtimestamp(sample.value, UTC)
        value = sample.value
        return int(value) if value.is_integer() else value

    @property
    def last_reset(self) -> datetime | None:
        """Start of the current day/month for periodically restarting totals."""
        sample = self.sample
        if sample is None or not sample.metric.reset or self._attr_state_class != SensorStateClass.TOTAL:
            return None
        tz = UTC if sample.metric.name in UTC_RESET_METRICS else _zone(self.coordinator.data.timezone)
        now = datetime.now(tz)
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        if sample.metric.reset == "month":
            start = start.replace(day=1)
        return start


def _zone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo("UTC")
