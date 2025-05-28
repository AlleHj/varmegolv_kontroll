"""
Golvvärmekontroll Integration
2025-05-28 2.3.0
"""
import logging

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, CONF_NAME, DEFAULT_TARGET_TEMP, CONF_TARGET_TEMP, DEFAULT_NAME, DEFAULT_DEBUG_LOGGING, CONF_DEBUG_LOGGING

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["climate"]

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Sätt upp Golvvärmekontroll-komponenten från YAML (används ej för UI-konfig)."""
    hass.data.setdefault(DOMAIN, {})
    _LOGGER.info(f"Golvvarmekontroll-komponenten (domän: {DOMAIN}) registreras.")
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Sätt upp Golvvärmekontroll från en config entry."""
    _LOGGER.info(f"Sätter upp Golvvarmekontroll-post '{entry.title}' (v{entry.version}, ID: {entry.entry_id}, Options: {entry.options})")
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _LOGGER.info(f"Golvvarmekontroll-post '{entry.title}' har satts upp framgångsrikt.")
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Ladda ur en config entry."""
    _LOGGER.info(f"Laddar ur Golvvarmekontroll-post '{entry.title}' (ID: {entry.entry_id})")
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        _LOGGER.info(f"Golvvarmekontroll-post '{entry.title}' har laddats ur framgångsrikt.")
    else:
        _LOGGER.error(f"Misslyckades med att ladda ur plattformar för Golvvarmekontroll-post '{entry.title}'.")
    return unload_ok

async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrera en gammal config entry."""
    _LOGGER.debug(f"Kontrollerar migrering för '{config_entry.title}' från v{config_entry.version} (data: {config_entry.data}, options: {config_entry.options})")

    if config_entry.version == 1:
        _LOGGER.info(f"Migrerar config entry '{config_entry.title}' från v1 till v2-databasen.")
        new_data = {**config_entry.data}
        new_options = {**config_entry.options}
        new_data.pop("thermostat_entity_id", None)
        new_options.pop("thermostat_entity_id", None)
        if CONF_NAME not in new_data:
            new_data[CONF_NAME] = config_entry.title or DEFAULT_NAME
        if CONF_TARGET_TEMP not in new_data:
            new_data[CONF_TARGET_TEMP] = DEFAULT_TARGET_TEMP
        if CONF_DEBUG_LOGGING not in new_options: # Säkerställ att nya optionen finns
            new_options[CONF_DEBUG_LOGGING] = DEFAULT_DEBUG_LOGGING

        config_entry.version = 2
        hass.config_entries.async_update_entry(config_entry, data=new_data, options=new_options)
        _LOGGER.info(f"Migrering av '{config_entry.title}' till v2-databasen slutförd.")
        _LOGGER.debug(f"Migrerad config_entry: data={new_data}, options={new_options}")
        return True # Viktigt att returnera True efter lyckad migrering

    # Om en config_entry är version 2 men saknar den nya debug-optionen (skapades innan 2.3.0)
    # Detta är relevant om config_flow.VERSION är 2 och vi lade till nya options
    # utan att bumpa VERSION i config_flow (vilket är standard om datastrukturen är kompatibel).
    if config_entry.version == 2 and CONF_DEBUG_LOGGING not in config_entry.options:
        _LOGGER.info(f"Uppdaterar config entry '{config_entry.title}' (v{config_entry.version}) för att inkludera default för '{CONF_DEBUG_LOGGING}'.")
        new_options = {**config_entry.options, CONF_DEBUG_LOGGING: DEFAULT_DEBUG_LOGGING}
        hass.config_entries.async_update_entry(config_entry, options=new_options)
        _LOGGER.info(f"'{CONF_DEBUG_LOGGING}' tillagd med defaultvärde för '{config_entry.title}'.")
        _LOGGER.debug(f"Uppdaterad config_entry options: {new_options}")
        return True # Viktigt att returnera True efter lyckad "mini-migrering"

    return True # Ingen migrering nödvändig eller redan hanterad