"""Binary sensors: daily writing goal reached, per user."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import GOAL_METRIC
from .coordinator import SchreibwerkstattConfigEntry, SchreibwerkstattCoordinator
from .entity import SchreibwerkstattEntity, instance_key
from .models import Sample


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SchreibwerkstattConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """One goal sensor per user with a daily goal; more appear when goals are set."""
    coordinator = entry.runtime_data
    known: set[str] = set()

    @callback
    def _add_new() -> None:
        new = []
        for key, sample in coordinator.data.samples.items():
            if sample.metric.name != GOAL_METRIC or key in known:
                continue
            known.add(key)
            new.append(DailyGoalReachedSensor(coordinator, sample))
        if new:
            async_add_entities(new)

    _add_new()
    entry.async_on_unload(coordinator.async_add_listener(_add_new))


class DailyGoalReachedSensor(SchreibwerkstattEntity, BinarySensorEntity):
    """On once today's writing time reaches the user's daily goal."""

    _attr_translation_key = "daily_goal_reached"

    def __init__(self, coordinator: SchreibwerkstattCoordinator, sample: Sample) -> None:
        super().__init__(coordinator, sample)
        self._attr_unique_id = f"{instance_key(coordinator)}_daily_goal_reached_{sample.user}"

    @property
    def is_on(self) -> bool | None:
        sample = self.sample
        return None if sample is None else sample.value >= 100
