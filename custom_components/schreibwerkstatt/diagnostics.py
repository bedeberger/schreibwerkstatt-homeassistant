"""Diagnostics: configuration and metric inventory, token and users redacted."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_API_TOKEN
from homeassistant.core import HomeAssistant

from .coordinator import SchreibwerkstattConfigEntry

TO_REDACT = {CONF_API_TOKEN}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: SchreibwerkstattConfigEntry
) -> dict[str, Any]:
    data = entry.runtime_data.data
    inventory: dict[str, int] = {}
    for sample in data.samples.values():
        inventory[sample.metric.name] = inventory.get(sample.metric.name, 0) + 1
    return {
        "entry": {
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": dict(entry.options),
        },
        "server": {
            "version": data.version,
            "timezone": data.timezone,
            "includes_users": data.includes_users,
            "user_count": len(data.users),
        },
        "metrics": dict(sorted(inventory.items())),
    }
