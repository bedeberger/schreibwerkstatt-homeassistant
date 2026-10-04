"""The Schreibwerkstatt integration: server, usage and cost metrics as sensors."""

from __future__ import annotations

import logging
import re

from homeassistant.const import CONF_API_TOKEN, CONF_URL, CONF_VERIFY_SSL, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv, device_registry as dr, entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from .api import SchreibwerkstattClient
from .const import DOMAIN
from .coordinator import SchreibwerkstattConfigEntry, SchreibwerkstattCoordinator
from .entity import instance_key, user_identifier
from .frontend import async_setup_frontend

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
# Up to 1.1 the user's display name was part of the unique ID.
_USER_NAME_LABEL = re.compile(r"\|user_name=[^|]*")


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Once per HA start: dashboard strategy (custom:schreibwerkstatt) and its data source."""
    await async_setup_frontend(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: SchreibwerkstattConfigEntry) -> bool:
    """Set up Schreibwerkstatt from a config entry."""
    session = async_get_clientsession(hass, verify_ssl=entry.data.get(CONF_VERIFY_SSL, True))
    client = SchreibwerkstattClient(session, entry.data[CONF_URL], entry.data[CONF_API_TOKEN])
    coordinator = SchreibwerkstattCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload))

    @callback
    def _sync_user_names() -> None:
        _async_sync_user_device_names(hass, coordinator)

    _sync_user_names()
    entry.async_on_unload(coordinator.async_add_listener(_sync_user_names))
    return True


async def async_migrate_entry(hass: HomeAssistant, entry: SchreibwerkstattConfigEntry) -> bool:
    """1.1 → 1.2: drop user_name from unique IDs, so a renamed user keeps entities and history."""
    if entry.version > 1:
        return False
    if entry.minor_version < 2:
        registry = er.async_get(hass)
        taken = {e.unique_id for e in er.async_entries_for_config_entry(registry, entry.entry_id)}

        @callback
        def _strip(entity: er.RegistryEntry) -> dict[str, str] | None:
            new = _USER_NAME_LABEL.sub("", entity.unique_id)
            if new == entity.unique_id:
                return None
            if new in taken:
                # Renamed before: the oldest entity (registry order) takes the ID and continues
                # its history; the later duplicate stays orphaned and can be deleted.
                _LOGGER.info("Not migrating %s: %s is already taken", entity.entity_id, new)
                return None
            taken.add(new)
            return {"new_unique_id": new}

        await er.async_migrate_entries(hass, entry.entry_id, _strip)
        hass.config_entries.async_update_entry(entry, minor_version=2)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: SchreibwerkstattConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_reload(hass: HomeAssistant, entry: SchreibwerkstattConfigEntry) -> None:
    """Options changed (scan interval): reload."""
    await hass.config_entries.async_reload(entry.entry_id)


@callback
def _async_sync_user_device_names(hass: HomeAssistant, coordinator: SchreibwerkstattCoordinator) -> None:
    """User devices follow the display name on the server (a rename in HA stays)."""
    registry = dr.async_get(hass)
    for email, name in coordinator.data.users.items():
        device = registry.async_get_device(identifiers={user_identifier(coordinator, email)})
        if device and device.name != name:
            registry.async_update_device(device.id, name=name)


async def async_remove_config_entry_device(
    hass: HomeAssistant, entry: SchreibwerkstattConfigEntry, device: dr.DeviceEntry
) -> bool:
    """Allow deleting the device of a user the server no longer reports."""
    coordinator: SchreibwerkstattCoordinator = entry.runtime_data
    prefix = f"{instance_key(coordinator)}_user_"
    current = {user_identifier(coordinator, email) for email in coordinator.data.users}
    is_user_device = any(ident[1].startswith(prefix) for ident in device.identifiers)
    return is_user_device and not (device.identifiers & current)
