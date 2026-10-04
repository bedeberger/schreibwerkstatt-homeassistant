"""Polling coordinator for Schreibwerkstatt."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SchreibwerkstattAuthError, SchreibwerkstattClient, SchreibwerkstattError
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN
from .models import MetricsData

_LOGGER = logging.getLogger(__name__)

type SchreibwerkstattConfigEntry = ConfigEntry[SchreibwerkstattCoordinator]


class SchreibwerkstattCoordinator(DataUpdateCoordinator[MetricsData]):
    """Fetches /metrics.json once per interval for all entities."""

    config_entry: SchreibwerkstattConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: SchreibwerkstattConfigEntry,
        client: SchreibwerkstattClient,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)),
        )
        self.client = client

    async def _async_update_data(self) -> MetricsData:
        try:
            raw = await self.client.async_get_metrics()
        except SchreibwerkstattAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except SchreibwerkstattError as err:
            raise UpdateFailed(str(err)) from err
        return MetricsData.from_json(raw)
