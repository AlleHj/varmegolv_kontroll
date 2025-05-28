"""Golvvärmekontroll Integration.

2025-05-28 2.3.3
"""
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType # Behålls om ConfigType används, annars onödig

from .const import ( # Importerat för migrering och setup_entry
    CONF_DEBUG_LOGGING,
    CONF_NAME,
    CONF_TARGET_TEMP,
    DEFAULT_DEBUG_LOGGING,
    DEFAULT_NAME,
    DEFAULT_TARGET_TEMP,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["climate"]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Sätt upp Golvvärmekontroll-komponenten från YAML (används generellt inte för UI-konfig)."""
    hass.data.setdefault(DOMAIN, {})
    _LOGGER.info("Golvvarmekontroll-komponenten (domän: %s) registreras.", DOMAIN) # G004
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Sätt upp Golvvärmekontroll från en config entry."""
    _LOGGER.info(
        "Sätter upp Golvvarmekontroll-post '%s' (v%s, ID: %s, Options: %s)",
        entry.title,
        entry.version,
        entry.entry_id,
        entry.options,
    ) # G004
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _LOGGER.info(
        "Golvvarmekontroll-post '%s' har satts upp framgångsrikt.", entry.title
    ) # G004
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Ladda ur en config entry."""
    _LOGGER.info(
        "Laddar ur Golvvarmekontroll-post '%s' (ID: %s)", entry.title, entry.entry_id
    ) # G004
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        _LOGGER.info(
            "Golvvarmekontroll-post '%s' har laddats ur framgångsrikt.", entry.title
        ) # G004
    else:
        _LOGGER.error(
            "Misslyckades med att ladda ur plattformar för Golvvarmekontroll-post '%s'.",
            entry.title,
        ) # G004
    return unload_ok


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrera en gammal config entry till senaste versionen."""
    _LOGGER.debug(
        "Kontrollerar migrering för '%s' från v%s (data: %s, options: %s)",
        config_entry.title,
        config_entry.version,
        config_entry.data,
        config_entry.options,
    ) # G004

    if config_entry.version == 1:
        _LOGGER.info(
            "Migrerar config entry '%s' från v1 till v2-databasen.", config_entry.title
        ) # G004
        new_data = {**config_entry.data}
        new_options = {**config_entry.options}
        new_data.pop("thermostat_entity_id", None)
        new_options.pop("thermostat_entity_id", None)
        if CONF_NAME not in new_data:
            new_data[CONF_NAME] = config_entry.title or DEFAULT_NAME
        if CONF_TARGET_TEMP not in new_data:
            new_data[CONF_TARGET_TEMP] = DEFAULT_TARGET_TEMP
        if CONF_DEBUG_LOGGING not in new_options:
            new_options[CONF_DEBUG_LOGGING] = DEFAULT_DEBUG_LOGGING

        config_entry.version = 2 # Målet för denna migrering
        hass.config_entries.async_update_entry(
            config_entry, data=new_data, options=new_options
        )
        _LOGGER.info(
            "Migrering av '%s' till v2-databasen slutförd.", config_entry.title
        ) # G004
        _LOGGER.debug("Migrerad config_entry: data=%s, options=%s", new_data, new_options) # G004
        return True

    if config_entry.version == 2 and CONF_DEBUG_LOGGING not in config_entry.options:
        _LOGGER.info(
            "Uppdaterar config entry '%s' (v%s) för att inkludera default för '%s'.",
            config_entry.title,
            config_entry.version,
            CONF_DEBUG_LOGGING,
        ) # G004
        new_options_v2_update = {
            **config_entry.options,
            CONF_DEBUG_LOGGING: DEFAULT_DEBUG_LOGGING,
        }
        hass.config_entries.async_update_entry(
            config_entry, options=new_options_v2_update
        )
        _LOGGER.info(
            "'%s' tillagd med defaultvärde för '%s'.",
            CONF_DEBUG_LOGGING,
            config_entry.title,
        ) # G004
        _LOGGER.debug("Uppdaterad config_entry options: %s", new_options_v2_update) # G004
        return True

    return True