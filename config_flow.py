"""Config flow för Golvvärmekontroll.

2025-05-28 2.3.7
"""

import logging

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.template import slugify

from .const import (
    CONF_DEBUG_LOGGING,
    CONF_HEATER_SWITCH_ENTITY,
    CONF_HYSTERESIS,
    CONF_MASTER_ENABLED,
    CONF_NAME,
    CONF_TARGET_TEMP,
    CONF_TEMP_SENSOR_ENTITY,
    DEFAULT_DEBUG_LOGGING,
    DEFAULT_HYSTERESIS,
    DEFAULT_NAME,
    DEFAULT_TARGET_TEMP,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

HELP_URL = (
    "https://github.com/AlleHj/home-assistant-varmegolv_kontroll/blob/master/HELP_sv.md"
)


class VarmegolvConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Hanterar konfigurationsflödet för Golvvärmekontroll."""

    VERSION = 2

    async def async_step_user(
        self, user_input: dict | None = None
    ) -> config_entries.ConfigFlowResult:
        """Hanterar det initiala användarsteget."""
        errors: dict[str, str] = {}
        if user_input is not None:
            name = user_input[CONF_NAME].strip()
            if not name:
                errors[CONF_NAME] = "name_empty"
            else:
                unique_id_candidate = f"{DOMAIN}_{slugify(name)}"
                await self.async_set_unique_id(unique_id_candidate)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=name,
                    data=user_input,
                    options={CONF_DEBUG_LOGGING: DEFAULT_DEBUG_LOGGING},
                )

        data_schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
                vol.Required(CONF_TEMP_SENSOR_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["sensor", "input_number"]),
                ),
                vol.Required(CONF_HEATER_SWITCH_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="switch"),
                ),
                vol.Optional(CONF_HYSTERESIS, default=DEFAULT_HYSTERESIS): vol.Coerce(
                    float
                ),
                vol.Optional(CONF_TARGET_TEMP, default=DEFAULT_TARGET_TEMP): vol.Coerce(
                    float
                ),
                vol.Optional(CONF_MASTER_ENABLED, default=True): bool,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "component_name": "Golvvärmekontroll",
                "help_url_text": f"För detaljerad information om konfigurationen, se [hjälpguiden]({HELP_URL}).",
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> "VarmegolvOptionsFlowHandler":
        """Hämta options-flödeshanteraren."""
        return VarmegolvOptionsFlowHandler(config_entry)


class VarmegolvOptionsFlowHandler(config_entries.OptionsFlow):
    """Hanterar options-flödet för Golvvärmekontroll."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialisera options-flödeshanteraren."""
        # Raden nedan är borttagen då self.config_entry tillhandahålls av basklassen:
        # self.config_entry = config_entry
        # current_config sätts nu i async_step_init istället, eller så används self.config_entry direkt.
        # För att behålla current_config som en sammanslagning kan vi göra det i varje steg
        # eller förlita oss på att self.config_entry.options och self.config_entry.data används.
        # Vi kommer att använda self.config_entry direkt i async_step_init.

    async def async_step_init(
        self, user_input: dict | None = None
    ) -> config_entries.ConfigFlowResult:
        """Hanterar initialiseringen av options-flödet."""
        errors: dict[str, str] = {}
        # Använd self.config_entry (från basklassen) för att hämta aktuell konfiguration
        current_config = {**self.config_entry.data, **self.config_entry.options}

        if user_input is not None:
            options_data_to_save = {
                CONF_TEMP_SENSOR_ENTITY: user_input.get(CONF_TEMP_SENSOR_ENTITY),
                CONF_HEATER_SWITCH_ENTITY: user_input.get(CONF_HEATER_SWITCH_ENTITY),
                CONF_HYSTERESIS: user_input.get(CONF_HYSTERESIS),
                CONF_MASTER_ENABLED: user_input.get(CONF_MASTER_ENABLED),
                CONF_DEBUG_LOGGING: user_input.get(CONF_DEBUG_LOGGING),
            }
            _LOGGER.debug(
                "[%s] Sparar options: %s",
                self.config_entry.title,  # self.config_entry är tillgänglig
                options_data_to_save,
            )
            return self.async_create_entry(title="", data=options_data_to_save)

        temp_sensor = current_config.get(CONF_TEMP_SENSOR_ENTITY)
        heater_switch = current_config.get(CONF_HEATER_SWITCH_ENTITY)
        hysteresis = current_config.get(CONF_HYSTERESIS, DEFAULT_HYSTERESIS)
        master_enabled = current_config.get(CONF_MASTER_ENABLED, True)
        debug_logging = current_config.get(CONF_DEBUG_LOGGING, DEFAULT_DEBUG_LOGGING)

        options_schema = vol.Schema(
            {
                vol.Required(
                    CONF_TEMP_SENSOR_ENTITY, default=temp_sensor
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["sensor", "input_number"]),
                ),
                vol.Required(
                    CONF_HEATER_SWITCH_ENTITY, default=heater_switch
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="switch"),
                ),
                vol.Optional(CONF_HYSTERESIS, default=hysteresis): vol.Coerce(float),
                vol.Optional(CONF_MASTER_ENABLED, default=master_enabled): bool,
                vol.Optional(CONF_DEBUG_LOGGING, default=debug_logging): bool,
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=options_schema,
            errors=errors,
            description_placeholders={
                "component_name": self.config_entry.title,  # self.config_entry är tillgänglig
                "help_url_text": f"För detaljerad information om dessa alternativ, se [hjälpguiden]({HELP_URL}).",
            },
        )
