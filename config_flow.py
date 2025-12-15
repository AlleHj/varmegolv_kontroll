"""
Config flow för Golvvärmekontroll.

Versionshistorik:
(Tidigare versioner...)
2.1.0 - 2025-05-23 - Gjorde namnfältet obligatoriskt för att säkerställa unika instanser.
                     Använder det angivna namnet för att generera ett unikt ID för config entry.
                     Titeln på config entry sätts till det angivna namnet.
"""
import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector
#from homeassistant.util.slugify import slugify
from homeassistant.util import slugify

from .const import (
    DOMAIN,
    CONF_TEMP_SENSOR_ENTITY,
    CONF_HEATER_SWITCH_ENTITY,
    CONF_HYSTERESIS,
    CONF_MASTER_ENABLED,
    CONF_TARGET_TEMP,
    CONF_NAME,
    DEFAULT_HYSTERESIS,
    DEFAULT_NAME,
    DEFAULT_TARGET_TEMP,
)

_LOGGER = logging.getLogger(__name__)

class VarmegolvConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 2

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            name = user_input[CONF_NAME].strip()
            if not name:
                errors[CONF_NAME] = "name_empty"
            else:
                unique_id_candidate = f"{DOMAIN}_{slugify(name)}"
                await self.async_set_unique_id(unique_id_candidate)
                self._abort_if_unique_id_configured() 
                return self.async_create_entry(title=name, data=user_input)

        data_schema = vol.Schema({
            vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
            vol.Required(CONF_TEMP_SENSOR_ENTITY): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["sensor", "input_number"]),
            ),
            vol.Required(CONF_HEATER_SWITCH_ENTITY): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="switch"),
            ),
            vol.Optional(CONF_HYSTERESIS, default=DEFAULT_HYSTERESIS): vol.Coerce(float),
            vol.Optional(CONF_TARGET_TEMP, default=DEFAULT_TARGET_TEMP): vol.Coerce(float),
            vol.Optional(CONF_MASTER_ENABLED, default=True): bool,
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={"component_name": "Golvvärmekontroll"},
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return VarmegolvOptionsFlowHandler(config_entry)

class VarmegolvOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry):
        self.config_entry = config_entry
        self.current_data = {**config_entry.data, **config_entry.options}

    async def async_step_init(self, user_input=None):
        errors = {}
        if user_input is not None:
            options_data_to_save = {
                CONF_TEMP_SENSOR_ENTITY: user_input.get(CONF_TEMP_SENSOR_ENTITY),
                CONF_HEATER_SWITCH_ENTITY: user_input.get(CONF_HEATER_SWITCH_ENTITY),
                CONF_HYSTERESIS: user_input.get(CONF_HYSTERESIS),
                CONF_MASTER_ENABLED: user_input.get(CONF_MASTER_ENABLED),
            }
            return self.async_create_entry(title="", data=options_data_to_save)
        
        options_schema = vol.Schema({
            vol.Required(CONF_TEMP_SENSOR_ENTITY, default=self.current_data.get(CONF_TEMP_SENSOR_ENTITY)): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["sensor", "input_number"]),
            ),
            vol.Required(CONF_HEATER_SWITCH_ENTITY, default=self.current_data.get(CONF_HEATER_SWITCH_ENTITY)): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="switch"),
            ),
            vol.Optional(CONF_HYSTERESIS, default=self.current_data.get(CONF_HYSTERESIS, DEFAULT_HYSTERESIS)): vol.Coerce(float),
            vol.Optional(CONF_MASTER_ENABLED, default=self.current_data.get(CONF_MASTER_ENABLED, True)): bool,
        })

        return self.async_show_form(
            step_id="init",
            data_schema=options_schema,
            errors=errors,
            description_placeholders={"component_name": self.config_entry.title},
        )