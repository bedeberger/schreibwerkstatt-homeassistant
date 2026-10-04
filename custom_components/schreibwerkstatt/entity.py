"""Base entity and device mapping."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, GROUP_NAMES, USER_MODEL
from .coordinator import SchreibwerkstattCoordinator
from .models import Sample


def ui_lang(coordinator: SchreibwerkstattCoordinator) -> str:
    """Language for server-provided names: de for German setups, else en."""
    return "de" if (coordinator.hass.config.language or "").startswith("de") else "en"


def instance_key(coordinator: SchreibwerkstattCoordinator) -> str:
    """Stable prefix for identifiers (server instance_id, else the entry id)."""
    return coordinator.config_entry.unique_id or coordinator.config_entry.entry_id


def main_device_info(coordinator: SchreibwerkstattCoordinator) -> DeviceInfo:
    """The Schreibwerkstatt instance itself."""
    data = coordinator.data
    return DeviceInfo(
        identifiers={(DOMAIN, instance_key(coordinator))},
        name="Schreibwerkstatt",
        manufacturer="Schreibwerkstatt",
        model="Server",
        sw_version=data.label_value("sw_build_info", "version") or data.version,
        configuration_url=coordinator.client.url,
        entry_type=DeviceEntryType.SERVICE,
    )


def user_identifier(coordinator: SchreibwerkstattCoordinator, email: str) -> tuple[str, str]:
    """Device identifier of one user."""
    return (DOMAIN, f"{instance_key(coordinator)}_user_{email}")


def device_info_for(coordinator: SchreibwerkstattCoordinator, sample: Sample) -> DeviceInfo:
    """Device a sample belongs to: main, group or user device."""
    root = instance_key(coordinator)
    lang = ui_lang(coordinator)
    group = sample.metric.group
    if group == "server":
        return main_device_info(coordinator)
    if group == "user" and sample.user:
        return DeviceInfo(
            identifiers={user_identifier(coordinator, sample.user)},
            name=sample.labels.get("user_name") or sample.user,
            manufacturer="Schreibwerkstatt",
            model=USER_MODEL[lang],
            via_device=(DOMAIN, root),
            entry_type=DeviceEntryType.SERVICE,
        )
    return DeviceInfo(
        identifiers={(DOMAIN, f"{root}_{group}")},
        name=f"Schreibwerkstatt {GROUP_NAMES[lang].get(group, group)}",
        manufacturer="Schreibwerkstatt",
        model=GROUP_NAMES[lang].get(group, group),
        via_device=(DOMAIN, root),
        entry_type=DeviceEntryType.SERVICE,
    )


class SchreibwerkstattEntity(CoordinatorEntity[SchreibwerkstattCoordinator]):
    """Entity bound to one sample key of the metrics document."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: SchreibwerkstattCoordinator, sample: Sample) -> None:
        super().__init__(coordinator)
        self._key = sample.key
        self._attr_device_info = device_info_for(coordinator, sample)

    @property
    def sample(self) -> Sample | None:
        """Current sample, None if the server no longer reports it."""
        return self.coordinator.data.samples.get(self._key)

    @property
    def available(self) -> bool:
        return super().available and self.sample is not None
