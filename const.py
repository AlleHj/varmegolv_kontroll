"""
Versionshistorik:
1.0.0 - 2025-05-23 - Initialversion. Definierar DOMAIN och konfigurationsnycklar.
1.0.1 - 2025-05-23 - Lade till DEFAULT_HYSTERESIS och STATE_MASTER_ENABLED.
2.0.0 - 2025-05-23 - Stor omarbetning: Komponenten agerar nu som en egen termostat.
                     CONF_THERMOSTAT_ENTITY borttagen.
                     Lade till DEFAULT_TARGET_TEMP.
2.1.0 - 2025-05-23 - Lade till CONF_NAME för unika instansnamn.
"""

DOMAIN = "varmegolv_kontroll"

# Konfigurationsnycklar
CONF_TEMP_SENSOR_ENTITY = "temp_sensor_entity_id"
CONF_HEATER_SWITCH_ENTITY = "heater_switch_entity_id"
CONF_HYSTERESIS = "hysteresis"
CONF_MASTER_ENABLED = "master_enabled"
CONF_TARGET_TEMP = "target_temp"
CONF_NAME = "name" # Nyckel för namnet på instansen

# Standardvärden
DEFAULT_NAME = "Golvvärmekontroll"
DEFAULT_HYSTERESIS = 0.5
DEFAULT_TARGET_TEMP = 20.0