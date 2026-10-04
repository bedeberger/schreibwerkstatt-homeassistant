"""The Schreibwerkstatt integration: server, usage and cost metrics as sensors."""

from __future__ import annotations

from homeassistant.const import CONF_API_TOKEN, CONF_URL, CONF_VERIFY_SSL, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SchreibwerkstattClient
from .coordinator import SchreibwerkstattConfigEntry, SchreibwerkstattCoordinator
from .entity import instance_key, user_identifier

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: SchreibwerkstattConfigEntry) -> bool:
    """Set up Schreibwerkstatt from a config entry."""
    session = async_get_clientsession(hass, verify_ssl=entry.data.get(CONF_VERIFY_SSL, True))
    client = SchreibwerkstattClient(session, entry.data[CONF_URL], entry.data[CONF_API_TOKEN])
    coordinator = SchreibwerkstattCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: SchreibwerkstattConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_reload(hass: HomeAssistant, entry: SchreibwerkstattConfigEntry) -> None:
    """Options changed (scan interval): reload."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_remove_config_entry_device(
    hass: HomeAssistant, entry: SchreibwerkstattConfigEntry, device: dr.DeviceEntry
) -> bool:
    """Allow deleting the device of a user the server no longer reports."""
    coordinator: SchreibwerkstattCoordinator = entry.runtime_data
    prefix = f"{instance_key(coordinator)}_user_"
    current = {user_identifier(coordinator, email) for email in coordinator.data.users}
    is_user_device = any(ident[1].startswith(prefix) for ident in device.identifiers)
    return is_user_device and not (device.identifiers & current)
