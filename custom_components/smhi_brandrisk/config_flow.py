"""Config flow för SMHI Brandrisk."""
from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, CONF_LATITUDE, CONF_LONGITUDE, CONF_NAME


def _schema(hass: HomeAssistant) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(
                CONF_NAME,
                default="Brandrisk hemma",
            ): str,
            vol.Required(
                CONF_LATITUDE,
                default=hass.config.latitude,
            ): vol.Coerce(float),
            vol.Required(
                CONF_LONGITUDE,
                default=hass.config.longitude,
            ): vol.Coerce(float),
        }
    )


class SMHIBrandRiskConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Hanterar konfiguration av SMHI Brandrisk via UI."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            lat = user_input[CONF_LATITUDE]
            lon = user_input[CONF_LONGITUDE]

            # Validera koordinater – SMHI täcker Sverige (55–70 N, 10–25 E)
            if not (55.0 <= lat <= 70.0):
                errors[CONF_LATITUDE] = "invalid_latitude"
            elif not (10.0 <= lon <= 25.0):
                errors[CONF_LONGITUDE] = "invalid_longitude"
            else:
                await self.async_set_unique_id(f"{lat}_{lon}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_schema(self.hass),
            errors=errors,
        )
