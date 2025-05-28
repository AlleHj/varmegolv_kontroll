"""
Konstanter för Golvvärmekontroll integrationen.
2025-05-28 2.3.0
"""

DOMAIN = "varmegolv_kontroll"

# Konfigurationsnycklar
CONF_TEMP_SENSOR_ENTITY = "temp_sensor_entity_id"
CONF_HEATER_SWITCH_ENTITY = "heater_switch_entity_id"
CONF_HYSTERESIS = "hysteresis"
CONF_MASTER_ENABLED = "master_enabled"
CONF_TARGET_TEMP = "target_temp"
CONF_NAME = "name" # Nyckel för namnet på instansen
CONF_DEBUG_LOGGING = "debug_logging" # Nyckel för att aktivera/deaktivera debug-loggning

# Standardvärden
DEFAULT_NAME = "Golvvärmekontroll"
DEFAULT_HYSTERESIS = 0.5
DEFAULT_TARGET_TEMP = 20.0
DEFAULT_DEBUG_LOGGING = False