"""Config, reauth and options flow for Schreibwerkstatt."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any
from urllib.parse import urlparse

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_API_TOKEN, CONF_SCAN_INTERVAL, CONF_URL, CONF_VERIFY_SSL
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    SchreibwerkstattAuthError,
    SchreibwerkstattClient,
    SchreibwerkstattConnectionError,
    SchreibwerkstattNotSupportedError,
    SchreibwerkstattSchemaError,
    normalize_url,
)
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, MAX_SCAN_INTERVAL, MIN_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_URL): str,
        vol.Required(CONF_API_TOKEN): str,
        vol.Optional(CONF_VERIFY_SSL, default=True): bool,
    }
)
REAUTH_SCHEMA = vol.Schema({vol.Required(CONF_API_TOKEN): str})


async def _async_fetch(
    hass: HomeAssistant, url: str, token: str, verify_ssl: bool
) -> tuple[dict[str, Any] | None, str | None]:
    """Try one fetch; return (document, error key)."""
    session = async_get_clientsession(hass, verify_ssl=verify_ssl)
    try:
        return await SchreibwerkstattClient(session, url, token).async_get_metrics(), None
    except SchreibwerkstattAuthError:
        return None, "invalid_auth"
    except SchreibwerkstattNotSupportedError:
        return None, "not_supported"
    except SchreibwerkstattSchemaError:
        return None, "unsupported_schema"
    except SchreibwerkstattConnectionError:
        return None, "cannot_connect"
    except Exception:  # noqa: BLE001 - surface anything else as "unknown"
        _LOGGER.exception("Unexpected error while contacting Schreibwerkstatt")
        return None, "unknown"


class SchreibwerkstattConfigFlow(ConfigFlow, domain=DOMAIN):
    """Set up a Schreibwerkstatt instance by URL and API token."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            url = normalize_url(user_input[CONF_URL])
            token = user_input[CONF_API_TOKEN].strip()
            verify = user_input.get(CONF_VERIFY_SSL, True)
            doc, error = await _async_fetch(self.hass, url, token, verify)
            if error:
                errors["base"] = error
            else:
                assert doc is not None
                # instance_id survives URL changes; older servers fall back to the URL.
                await self.async_set_unique_id(doc.get("instance_id") or url)
                self._abort_if_unique_id_configured(updates={CONF_URL: url})
                return self.async_create_entry(
                    title=urlparse(url).hostname or "Schreibwerkstatt",
                    data={CONF_URL: url, CONF_API_TOKEN: token, CONF_VERIFY_SSL: verify},
                )
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(USER_SCHEMA, user_input),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        """The token was revoked or expired."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            token = user_input[CONF_API_TOKEN].strip()
            _doc, error = await _async_fetch(
                self.hass, entry.data[CONF_URL], token, entry.data.get(CONF_VERIFY_SSL, True)
            )
            if error:
                errors["base"] = error
            else:
                return self.async_update_reload_and_abort(entry, data_updates={CONF_API_TOKEN: token})
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=REAUTH_SCHEMA,
            errors=errors,
            description_placeholders={"url": entry.data[CONF_URL]},
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return SchreibwerkstattOptionsFlow()


class SchreibwerkstattOptionsFlow(OptionsFlow):
    """Polling interval."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        current = self.config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SCAN_INTERVAL, default=current): vol.All(
                        vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL)
                    )
                }
            ),
        )
