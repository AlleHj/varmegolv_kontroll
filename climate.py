"""
Climate-plattform för Golvvärmekontroll.

Versionshistorik:
(Tidigare versioner)
2.2.1 - 2025-05-23 - Explicit _attr_name = None i climate.py för tydlighet i namngivning.
2.2.2 - 2025-05-24 - Fix: Korrigerat TypeError i _perform_initial_updates_and_control
                     genom att ta bort felaktigt 'await' på synkron funktion.
"""
import logging
import functools
from typing import Any, Optional, List

from homeassistant.components.climate import (
    ClimateEntity, ClimateEntityFeature, HVACMode, HVACAction,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfTemperature, ATTR_TEMPERATURE, STATE_UNAVAILABLE, STATE_UNKNOWN,
    EVENT_HOMEASSISTANT_START,
)
from homeassistant.core import HomeAssistant, callback, Event, State
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    DOMAIN, CONF_TEMP_SENSOR_ENTITY, CONF_HEATER_SWITCH_ENTITY, CONF_HYSTERESIS,
    CONF_MASTER_ENABLED, CONF_TARGET_TEMP, DEFAULT_HYSTERESIS, DEFAULT_TARGET_TEMP,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback,
) -> None:
    _LOGGER.info(f"Sätter upp climate-entitet för '{config_entry.title}' ({config_entry.entry_id}) v{config_entry.version}")
    config_data = {**config_entry.data, **config_entry.options}
    controller = VarmegolvClimate(hass, config_entry, config_data)
    async_add_entities([controller], True)

class VarmegolvClimate(ClimateEntity, RestoreEntity):
    _attr_has_entity_name = True
    _attr_name = None

    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE |
        ClimateEntityFeature.TURN_ON |
        ClimateEntityFeature.TURN_OFF
    )

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry, config_data: dict) -> None:
        self.hass = hass
        self._config_entry = config_entry
        self._config_data = config_data
        self._attr_name = None
        self._temp_sensor_entity_id = self._config_data.get(CONF_TEMP_SENSOR_ENTITY)
        self._heater_switch_entity_id = self._config_data.get(CONF_HEATER_SWITCH_ENTITY)
        self._hysteresis = self._config_data.get(CONF_HYSTERESIS, DEFAULT_HYSTERESIS)
        self._attr_unique_id = f"{config_entry.entry_id}_thermostat"
        self._attr_temperature_unit = hass.config.units.temperature_unit
        self._current_temp: Optional[float] = None
        self._target_temp: float = self._config_data.get(CONF_TARGET_TEMP, DEFAULT_TARGET_TEMP)
        initial_master_enabled = self._config_data.get(CONF_MASTER_ENABLED, True)
        self._attr_hvac_mode: HVACMode = HVACMode.HEAT if initial_master_enabled else HVACMode.OFF
        self._attr_hvac_action: Optional[HVACAction] = None
        self._listeners = []
        _LOGGER.debug(f"[{self._config_entry.title}] __init__: TargetTemp={self._target_temp}, HVACMode={self._attr_hvac_mode}")

    @property
    def device_info(self):
        return {"identifiers": {(DOMAIN, self._config_entry.entry_id)}, "name": self._config_entry.title, "manufacturer": "Anpassad Komponent AB", "model": "Golvvärmetermostat v2.2", "sw_version": self._config_entry.version}
    @property
    def current_temperature(self) -> Optional[float]: return self._current_temp
    @property
    def target_temperature(self) -> Optional[float]: return self._target_temp
    @property
    def hvac_mode(self) -> HVACMode: return self._attr_hvac_mode
    @property
    def hvac_action(self) -> Optional[HVACAction]:
        if self._attr_hvac_mode == HVACMode.OFF: return HVACAction.OFF
        if self._heater_switch_entity_id:
            heater_state = self.hass.states.get(self._heater_switch_entity_id)
            if heater_state and heater_state.state == "on": return HVACAction.HEATING
        return HVACAction.IDLE

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        _LOGGER.debug(f"[{self._config_entry.title}] async_added_to_hass: Startar.")
        initial_target_temp_from_config = self._config_data.get(CONF_TARGET_TEMP, DEFAULT_TARGET_TEMP)
        initial_master_enabled_from_config = self._config_data.get(CONF_MASTER_ENABLED, True)
        last_state = await self.async_get_last_state()
        if last_state:
            _LOGGER.debug(f"[{self._config_entry.title}] Återställer från last_state: {last_state.attributes}")
            self._target_temp = float(last_state.attributes.get(ATTR_TEMPERATURE, initial_target_temp_from_config))
            restored_hvac_mode_str = last_state.attributes.get("hvac_mode")
            if restored_hvac_mode_str:
                try: self._attr_hvac_mode = HVACMode(restored_hvac_mode_str)
                except ValueError:
                    _LOGGER.warning(f"[{self._config_entry.title}] Ogiltigt HVAC-läge '{restored_hvac_mode_str}' återställt, använder från config.")
                    self._attr_hvac_mode = HVACMode.HEAT if initial_master_enabled_from_config else HVACMode.OFF
            else:
                _LOGGER.debug(f"[{self._config_entry.title}] Inget HVAC-läge i last_state, använder från config.")
                self._attr_hvac_mode = HVACMode.HEAT if initial_master_enabled_from_config else HVACMode.OFF
        else:
            _LOGGER.debug(f"[{self._config_entry.title}] Inget last_state, använder initiala konfigurationsvärden.")
            self._target_temp = initial_target_temp_from_config
            self._attr_hvac_mode = HVACMode.HEAT if initial_master_enabled_from_config else HVACMode.OFF
        _LOGGER.debug(f"[{self._config_entry.title}] Efter återställning/init: TargetTemp={self._target_temp}, HVACMode={self._attr_hvac_mode}")
        self._config_entry.async_on_unload(self._config_entry.add_update_listener(self._async_options_updated))
        self._setup_sensor_listeners()
        if not self.hass.is_running:
            _LOGGER.debug(f"[{self._config_entry.title}] HA ej startat, reg. EVENT_HOMEASSISTANT_START listener.")
            start_listener_unsub = self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_START, self._async_home_assistant_started)
            self._listeners.append(start_listener_unsub)
        else:
            _LOGGER.debug(f"[{self._config_entry.title}] HA körs, anropar _perform_initial_updates_and_control direkt.")
            await self._perform_initial_updates_and_control()

    async def _perform_initial_updates_and_control(self): # Är async
        _LOGGER.debug(f"[{self._config_entry.title}] _perform_initial_updates_and_control anropad.")
        if self._temp_sensor_entity_id:
            temp_sensor_state = self.hass.states.get(self._temp_sensor_entity_id)
            if temp_sensor_state:
                # KORRIGERING HÄR: _update_from_temp_sensor_state är synkron
                self._update_from_temp_sensor_state(temp_sensor_state)
        await self._control_heating()
        self.async_schedule_update_ha_state(True)

    def _setup_sensor_listeners(self):
        _LOGGER.debug(f"[{self._config_entry.title}] Sätter upp sensorlyssnare.")
        self._remove_listeners()
        if self._temp_sensor_entity_id: self._listeners.append(async_track_state_change_event(self.hass, self._temp_sensor_entity_id, self._async_temp_sensor_changed))
        if self._heater_switch_entity_id: self._listeners.append(async_track_state_change_event(self.hass, self._heater_switch_entity_id, self._async_heater_switch_changed))

    async def _async_home_assistant_started(self, event: Event):
        _LOGGER.debug(f"[{self._config_entry.title}] Event: Home Assistant startad fullt ut.")
        await self._perform_initial_updates_and_control()

    async def async_will_remove_from_hass(self) -> None:
        _LOGGER.debug(f"[{self._config_entry.title}] async_will_remove_from_hass: Tar bort lyssnare.")
        self._remove_listeners()
        await super().async_will_remove_from_hass()

    def _remove_listeners(self):
        while self._listeners: self._listeners.pop()()

    @callback
    async def _update_config_from_options(self):
        _LOGGER.debug(f"[{self._config_entry.title}] _update_config_from_options: Laddar om konfiguration från options.")
        self._config_data = {**self._config_entry.data, **self._config_entry.options}
        new_temp_sensor = self._config_data.get(CONF_TEMP_SENSOR_ENTITY)
        new_heater_switch = self._config_data.get(CONF_HEATER_SWITCH_ENTITY)
        listeners_need_reset = False
        if self._temp_sensor_entity_id != new_temp_sensor:
            self._temp_sensor_entity_id = new_temp_sensor
            listeners_need_reset = True
            _LOGGER.info(f"[{self._config_entry.title}] Temperatursensor ändrad till: {new_temp_sensor}")
        if self._heater_switch_entity_id != new_heater_switch:
            self._heater_switch_entity_id = new_heater_switch
            listeners_need_reset = True
            _LOGGER.info(f"[{self._config_entry.title}] Värmeswitch ändrad till: {new_heater_switch}")
        self._hysteresis = self._config_data.get(CONF_HYSTERESIS, DEFAULT_HYSTERESIS)
        new_master_enabled_option = self._config_entry.options.get(CONF_MASTER_ENABLED)
        if new_master_enabled_option is not None:
            target_hvac_mode = HVACMode.HEAT if new_master_enabled_option else HVACMode.OFF
            if self._attr_hvac_mode != target_hvac_mode:
                self._attr_hvac_mode = target_hvac_mode
                _LOGGER.info(f"[{self._config_entry.title}] HVAC-läge uppdaterat till {self._attr_hvac_mode} via options-ändring.")
        if listeners_need_reset:
            _LOGGER.debug(f"[{self._config_entry.title}] Återställer sensorlyssnare pga options-ändring.")
            self._setup_sensor_listeners()
            if self.hass.is_running: await self._perform_initial_updates_and_control()

    @callback
    async def _async_options_updated(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        _LOGGER.info(f"[{self._config_entry.title}] _async_options_updated: Options har ändrats, applicerar.")
        await self._update_config_from_options()
        await self._control_heating()
        self.async_schedule_update_ha_state()

    @callback
    async def _async_temp_sensor_changed(self, event: Event) -> None:
        new_state: Optional[State] = event.data.get("new_state")
        _LOGGER.debug(f"[{self._config_entry.title}] Tempsensor '{self._temp_sensor_entity_id}' ändrades: {new_state.state if new_state else 'None'}")
        # KORRIGERING HÄR: _update_from_temp_sensor_state är synkron
        if self._update_from_temp_sensor_state(new_state):
            await self._control_heating()
            self.async_schedule_update_ha_state()

    def _update_from_temp_sensor_state(self, state: Optional[State]) -> bool: # Denna är synkron
        changed = False
        if state and state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            try:
                current_temp = float(state.state)
                if self._current_temp != current_temp:
                    self._current_temp = current_temp
                    _LOGGER.debug(f"[{self._config_entry.title}] Aktuell temperatur {self._current_temp}°C från {self._temp_sensor_entity_id}")
                    changed = True
            except ValueError:
                _LOGGER.warning(f"[{self._config_entry.title}] Kunde inte tolka temp från {self._temp_sensor_entity_id}: {state.state}")
                if self._current_temp is not None: changed = True
                self._current_temp = None
        elif self._current_temp is not None:
            _LOGGER.warning(f"[{self._config_entry.title}] Temperatursensor {self._temp_sensor_entity_id} otillgänglig.")
            self._current_temp = None
            changed = True
        return changed

    @callback
    def _async_heater_switch_changed(self, event: Event) -> None:
        new_state_obj: Optional[State] = event.data.get("new_state")
        switch_state = new_state_obj.state if new_state_obj else "okänt (ingen state)"
        _LOGGER.info(f"[{self._config_entry.title}] Värmeswitch '{self._heater_switch_entity_id}' ändrades till '{switch_state}'. Förbereder schemaläggning av HA-statusuppdatering.")
        try:
            self.async_schedule_update_ha_state()
            _LOGGER.info(f"[{self._config_entry.title}] async_schedule_update_ha_state ANROPAD från _async_heater_switch_changed.")
        except Exception as e:
            _LOGGER.error(f"[{self._config_entry.title}] FEL vid anrop av async_schedule_update_ha_state i _async_heater_switch_changed: {e}", exc_info=True)

    async def _control_heating(self) -> None:
        if self._attr_hvac_mode != HVACMode.HEAT:
            _LOGGER.debug(f"[{self._config_entry.title}] HVAC-läge {self._attr_hvac_mode}, styr ej värme.")
            if self._heater_switch_entity_id:
                current_heater_state_obj = self.hass.states.get(self._heater_switch_entity_id)
                if current_heater_state_obj and current_heater_state_obj.state == "on":
                    _LOGGER.info(f"[{self._config_entry.title}] Termostat är AV, stänger av värmare {self._heater_switch_entity_id}.")
                    await self._set_heater_state(False)
            return
        if self._current_temp is None or self._target_temp is None:
            _LOGGER.debug(f"[{self._config_entry.title}] Temp ({self._current_temp}) eller mål ({self._target_temp}) okänd. Kan ej styra.")
            return
        if not self._heater_switch_entity_id:
            _LOGGER.warning(f"[{self._config_entry.title}] Ingen värmeswitch konfigurerad för styrning.")
            return
        heater_state_obj = self.hass.states.get(self._heater_switch_entity_id)
        if not heater_state_obj:
            _LOGGER.warning(f"[{self._config_entry.title}] Värmeswitch {self._heater_switch_entity_id} ej hittad i HA:s tillstånd.")
            return
        is_heater_on = heater_state_obj.state == "on"
        _LOGGER.debug(f"[{self._config_entry.title}] Styrlogik: Akt: {self._current_temp}°C, Mål: {self._target_temp}°C, Hys: {self._hysteresis}°C, Värmare: {'PÅ' if is_heater_on else 'AV'}")
        lower_bound = self._target_temp - (self._hysteresis / 2)
        upper_bound = self._target_temp + (self._hysteresis / 2)
        desired_action_turn_on = None
        if is_heater_on:
            if self._current_temp >= upper_bound:
                _LOGGER.info(f"[{self._config_entry.title}] Temp {self._current_temp}°C >= {upper_bound}°C. Önskar stänga AV.")
                desired_action_turn_on = False
        else:
            if self._current_temp <= lower_bound:
                _LOGGER.info(f"[{self._config_entry.title}] Temp {self._current_temp}°C <= {lower_bound}°C. Önskar slå PÅ.")
                desired_action_turn_on = True
        if desired_action_turn_on is True:
            _LOGGER.info(f"[{self._config_entry.title}] Värmaren är AV, men önskas PÅ. Anropar _set_heater_state(True).")
            await self._set_heater_state(True)
        elif desired_action_turn_on is False:
            _LOGGER.info(f"[{self._config_entry.title}] Värmaren är PÅ, men önskas AV. Anropar _set_heater_state(False).")
            await self._set_heater_state(False)
        else:
            _LOGGER.debug(f"[{self._config_entry.title}] Värmarens nuvarande tillstånd matchar önskat tillstånd. Ingen åtgärd.")

    async def _set_heater_state(self, turn_on: bool) -> None:
        if not self._heater_switch_entity_id:
            _LOGGER.warning(f"[{self._config_entry.title}] Ingen värmeswitch konfigurerad, kan inte ändra status.")
            return
        service_to_call = "turn_on" if turn_on else "turn_off"
        entity_id_to_call = self._heater_switch_entity_id
        _LOGGER.info(f"[{self._config_entry.title}] FÖRBEREDER anrop (via executor) till switch.{service_to_call} för '{entity_id_to_call}' (BLOCKING=TRUE, UTAN KONTEXT).")
        try:
            await self.hass.async_add_executor_job(
                functools.partial(
                    self.hass.services.call, "switch", service_to_call,
                    {"entity_id": entity_id_to_call}, True, None
                )
            )
            _LOGGER.info(f"[{self._config_entry.title}] ANROP (via executor) TILL switch.{service_to_call} för '{entity_id_to_call}' HAR SLUTFÖRTS.")
        except Exception as e:
            _LOGGER.error(f"[{self._config_entry.title}] FEL vid anrop (via executor) till switch.{service_to_call} för '{entity_id_to_call}': {e}", exc_info=True)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        temperature = kwargs.get(ATTR_TEMPERATURE)
        _LOGGER.debug(f"[{self._config_entry.title}] async_set_temperature anropad med: {kwargs}")
        if temperature is None:
            _LOGGER.debug(f"[{self._config_entry.title}] Ingen temperatur angiven i async_set_temperature.")
            return
        new_target_temp = float(temperature)
        if new_target_temp == self._target_temp:
            _LOGGER.debug(f"[{self._config_entry.title}] Måltemperatur redan {new_target_temp}°C, ingen ändring.")
            return
        self._target_temp = new_target_temp
        _LOGGER.info(f"[{self._config_entry.title}] Ny måltemperatur satt internt till {self._target_temp}°C. Anropar _control_heating.")
        await self._control_heating()
        _LOGGER.info(f"[{self._config_entry.title}] async_set_temperature: Efter _control_heating. Förbereder async_write_ha_state för måltemp {self._target_temp}°C.")
        try:
            self.async_write_ha_state()
            _LOGGER.info(f"[{self._config_entry.title}] async_set_temperature: async_write_ha_state ANROPAD för måltemp {self._target_temp}°C.")
        except Exception as e:
            _LOGGER.error(f"[{self._config_entry.title}] FEL vid anrop av async_write_ha_state i async_set_temperature: {e}", exc_info=True)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        _LOGGER.debug(f"[{self._config_entry.title}] async_set_hvac_mode anropad med: {hvac_mode}")
        if hvac_mode not in self._attr_hvac_modes:
            _LOGGER.warning(f"[{self._config_entry.title}] HVAC-läge {hvac_mode} stöds ej.")
            return
        if hvac_mode == self._attr_hvac_mode:
            _LOGGER.debug(f"[{self._config_entry.title}] HVAC-läge redan {hvac_mode}, ingen ändring.")
            return
        _LOGGER.info(f"[{self._config_entry.title}] Sätter HVAC-läge internt till {hvac_mode}.")
        self._attr_hvac_mode = hvac_mode
        new_options = {**self._config_entry.options}
        new_options[CONF_MASTER_ENABLED] = (hvac_mode == HVACMode.HEAT)
        _LOGGER.debug(f"[{self._config_entry.title}] Uppdaterar config_entry options med CONF_MASTER_ENABLED={new_options[CONF_MASTER_ENABLED]}")
        self.hass.config_entries.async_update_entry(self._config_entry, options=new_options)
        await self._control_heating()
        self.async_write_ha_state()
        _LOGGER.debug(f"[{self._config_entry.title}] async_write_ha_state anropad efter HVAC-lägesändring.")

    async def async_turn_on(self) -> None:
        _LOGGER.debug(f"[{self._config_entry.title}] async_turn_on anropad.")
        await self.async_set_hvac_mode(HVACMode.HEAT)

    async def async_turn_off(self) -> None:
        _LOGGER.debug(f"[{self._config_entry.title}] async_turn_off anropad.")
        await self.async_set_hvac_mode(HVACMode.OFF)