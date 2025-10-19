"""
Golvvärmekontroll Integration

Versionshistorik:
(Tidigare versioner...)
2.1.0 - 2025-05-23 - Tillåter flera instanser med unika namn. Namnfältet är nu obligatoriskt i konfigurationen.
2.1.2 - 2025-05-23 - Förhindrar onödig global omladdning av config entry när options (t.ex. HVAC-läge) ändras,
                     då climate-entiteten hanterar detta live. Detta bör minska "ValueError" för lyssnare.
"""
import logging

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, CONF_NAME, DEFAULT_TARGET_TEMP, CONF_TARGET_TEMP, DEFAULT_NAME # Importera för migrering

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["climate"]

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    hass.data.setdefault(DOMAIN, {})
    _LOGGER.info(f"Golvvarmekontroll-komponenten (domän: {DOMAIN}) registreras.")
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    _LOGGER.info(f"Sätter upp Golvvarmekontroll-post '{entry.title}' (v{entry.version}, ID: {entry.entry_id})")
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_options_update_listener))
    _LOGGER.info(f"Golvvarmekontroll-post '{entry.title}' har satts upp framgångsrikt.")
    return True

async def _options_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    _LOGGER.info(f"Global lyssnare: Alternativ uppdaterade för '{entry.title}'.")
    _LOGGER.debug(f"Global lyssnare för '{entry.title}': Ingen omladdning utförs, förlitar sig på live-hantering i entiteten.")

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    _LOGGER.info(f"Laddar ur Golvvarmekontroll-post '{entry.title}' (ID: {entry.entry_id})")
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        _LOGGER.info(f"Golvvarmekontroll-post '{entry.title}' har laddats ur framgångsrikt.")
    else:
        _LOGGER.error(f"Misslyckades med att ladda ur plattformar för Golvvarmekontroll-post '{entry.title}'.")
    return unload_ok

async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    _LOGGER.debug(f"Kontrollerar migrering för '{config_entry.title}' från v{config_entry.version}")
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
        config_entry.version = 2
        hass.config_entries.async_update_entry(config_entry, data=new_data, options=new_options)
        _LOGGER.info(f"Migrering av '{config_entry.title}' till v2-databasen slutförd.")
    return True