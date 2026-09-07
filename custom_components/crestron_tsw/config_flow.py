"""Config flow for Crestron TSW."""

from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT

from .const import CONF_IP_ID, DEFAULT_HOST, DEFAULT_IP_ID, DEFAULT_NAME, DEFAULT_PORT, DOMAIN


class CrestronTSWConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Configure the local CIP listener."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle setup from the UI."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            await self.async_set_unique_id("crestron-tsw-cip-listener")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
                vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=65535)
                ),
                vol.Required(CONF_IP_ID, default=DEFAULT_IP_ID): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=255)
                ),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)
