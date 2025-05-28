"""
Climate-plattform för Golvvärmekontroll.
2025-05-28 2.3.1
"""
import logging
import functools
from typing import Any, Optional, List, Callable

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
    CONF_MASTER_ENABLED, CONF_TARGET_TEMP, CONF_DEBUG_LOGGING, DEFAULT_HYSTERESIS,
    DEFAULT_TARGET_TEMP, DEFAULT_DEBUG_LOGGING
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback,
) -> None:
    _LOGGER.info(f"Sätter upp climate-entitet för '{config_entry.title}' ({config_entry.entry_id}) v{config_entry.version}")
    initial_config_data = {**config_entry.data, **config_entry.options}
    controller = VarmegolvClimate(hass, config_entry, initial_config_data)
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
        self._config_data = dict(config_data)
        self._temp_sensor_entity_id = self._config_data.get(CONF_TEMP_SENSOR_ENTITY)
        self._heater_switch_entity_id = self._config_data.get(CONF_HEATER_SWITCH_ENTITY)
        self._hysteresis = self._config_data.get(CONF_HYSTERESIS, DEFAULT_HYSTERESIS)
        self._debug_logging_enabled = self._config_data.get(CONF_DEBUG_LOGGING, DEFAULT_DEBUG_LOGGING)

        self._attr_unique_id = f"{config_entry.entry_id}_thermostat"
        self._attr_temperature_unit = hass.config.units.temperature_unit
        self._current_temp: Optional[float] = None
        self._target_temp: float = self._config_data.get(CONF_TARGET_TEMP, DEFAULT_TARGET_TEMP)
        initial_master_enabled = self._config_data.get(CONF_MASTER_ENABLED, True)
        self._attr_hvac_mode: HVACMode = HVACMode.HEAT if initial_master_enabled else HVACMode.OFF
        self._attr_hvac_action: Optional[HVACAction] = None
        self._listeners: List[Callable[[], None]] = []
        self._event_start_listener_unsub_handle: Optional[Callable[[], None]] = None # För EVENT_HOMEASSISTANT_START

        if self._debug_logging_enabled:
            _LOGGER.debug(f"[{self._config_entry.title}] __init__: TargetTemp={self._target_temp}, HVACMode={self._attr_hvac_mode}, DebugLog={self._debug_logging_enabled}")

    @property
    def device_info(self):
        # Använder self._config_entry.version för att reflektera versionen från manifestet
        return {"identifiers": {(DOMAIN, self._config_entry.entry_id)}, "name": self._config_entry.title, "manufacturer": "Anpassad Komponent AB (AlleHj)", "model": "Golvvärmetermostat", "sw_version": self._config_entry.version}

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
        if self._debug_logging_enabled:
            _LOGGER.debug(f"[{self._config_entry.title}] async_added_to_hass: Startar.")

        initial_target_temp_from_data = self._config_entry.data.get(CONF_TARGET_TEMP, DEFAULT_TARGET_TEMP)
        initial_master_enabled_from_data = self._config_entry.data.get(CONF_MASTER_ENABLED, True)
        initial_master_enabled_from_options = self._config_entry.options.get(CONF_MASTER_ENABLED, initial_master_enabled_from_data)

        last_state = await self.async_get_last_state()
        if last_state:
            if self._debug_logging_enabled:
                _LOGGER.debug(f"[{self._config_entry.title}] Återställer från last_state: {last_state.attributes}")
            self._target_temp = float(last_state.attributes.get(ATTR_TEMPERATURE, initial_target_temp_from_data))
            restored_hvac_mode_str = last_state.attributes.get("hvac_mode")
            if restored_hvac_mode_str:
                try: self._attr_hvac_mode = HVACMode(restored_hvac_mode_str)
                except ValueError:
                    _LOGGER.warning(f"[{self._config_entry.title}] Ogiltigt HVAC-läge '{restored_hvac_mode_str}' återställt, använder från config (options/data).")
                    self._attr_hvac_mode = HVACMode.HEAT if initial_master_enabled_from_options else HVACMode.OFF
            else:
                if self._debug_logging_enabled:
                    _LOGGER.debug(f"[{self._config_entry.title}] Inget HVAC-läge i last_state, använder från config (options/data).")
                self._attr_hvac_mode = HVACMode.HEAT if initial_master_enabled_from_options else HVACMode.OFF
        else:
            if self._debug_logging_enabled:
                _LOGGER.debug(f"[{self._config_entry.title}] Inget last_state, använder initiala konfigurationsvärden (data/options).")
            self._target_temp = initial_target_temp_from_data
            self._attr_hvac_mode = HVACMode.HEAT if initial_master_enabled_from_options else HVACMode.OFF

        if self._debug_logging_enabled:
            _LOGGER.debug(f"[{self._config_entry.title}] Efter återställning/init: TargetTemp={self._target_temp}, HVACMode={self._attr_hvac_mode}")

        self._config_entry.async_on_unload(self._config_entry.add_update_listener(self._async_options_updated_listener_proxy))

        if not self.hass.is_running:
            if self._debug_logging_enabled:
                _LOGGER.debug(f"[{self._config_entry.title}] HA ej startat, reg. EVENT_HOMEASSISTANT_START listener.")
            # Spara referensen till avregistreringsfunktionen specifikt
            self._event_start_listener_unsub_handle = self.hass.bus.async_listen_once(
                EVENT_HOMEASSISTANT_START, self._async_home_assistant_started
            )
            # Lägg fortfarande till den i den generella listan för _remove_listeners om komponenten tas bort innan HA startar.
            self._listeners.append(self._event_start_listener_unsub_handle)
        else:
            if self._debug_logging_enabled:
                _LOGGER.debug(f"[{self._config_entry.title}] HA körs, anropar _perform_initial_updates_and_control direkt.")
            # HA körs redan, så vi behöver inte lyssna på EVENT_HOMEASSISTANT_START
            # Kör initieringslogiken direkt
            await self._perform_initial_updates_and_control() # Detta saknades tidigare i denna else-gren

        self._setup_sensor_listeners() # Sätt upp lyssnare för sensorer EFTER eventuell startlistener är hanterad

    async def _async_options_updated_listener_proxy(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        if self._debug_logging_enabled:
             _LOGGER.debug(f"[{self._config_entry.title}] Options update listener proxy anropad. Gamla debug: {self._debug_logging_enabled}")
        await self._async_options_updated(hass, entry)

    async def _perform_initial_updates_and_control(self):
        if self._debug_logging_enabled:
            _LOGGER.debug(f"[{self._config_entry.title}] _perform_initial_updates_and_control anropad.")
        if self._temp_sensor_entity_id:
            temp_sensor_state = self.hass.states.get(self._temp_sensor_entity_id)
            if temp_sensor_state:
                self._update_from_temp_sensor_state(temp_sensor_state)
        await self._control_heating()
        self.async_schedule_update_ha_state(True)

    def _setup_sensor_listeners(self):
        if self._debug_logging_enabled:
            _LOGGER.debug(f"[{self._config_entry.title}] Sätter upp sensorlyssnare (rensa gamla först).")
        self._remove_listeners() # Rensa ALLA gamla lyssnare

        # Lägg till nya sensorlyssnare
        if self._temp_sensor_entity_id:
            unsub = async_track_state_change_event(self.hass, self._temp_sensor_entity_id, self._async_temp_sensor_changed)
            self._listeners.append(unsub)
            if self._debug_logging_enabled:
                _LOGGER.debug(f"[{self._config_entry.title}] Lade till lyssnare för tempsensor: {self._temp_sensor_entity_id}")

        if self._heater_switch_entity_id:
            unsub = async_track_state_change_event(self.hass, self._heater_switch_entity_id, self._async_heater_switch_changed)
            self._listeners.append(unsub)
            if self._debug_logging_enabled:
                _LOGGER.debug(f"[{self._config_entry.title}] Lade till lyssnare för värmeswitch: {self._heater_switch_entity_id}")

        # Återlägg EVENT_HOMEASSISTANT_START listener om den togs bort av _remove_listeners och fortfarande behövs
        # Detta hanteras nu bättre genom att _event_start_listener_unsub_handle tas bort från _listeners
        # när den har kört. Om _setup_sensor_listeners anropas innan HA startat och _event_start_listener_unsub_handle
        # finns, kommer _remove_listeners anropa den (vilket är OK, den avbryts).
        # Men den ska inte läggas till igen här, den sätts bara i async_added_to_hass.


    async def _async_home_assistant_started(self, event: Event):
        if self._debug_logging_enabled:
            _LOGGER.debug(f"[{self._config_entry.title}] Event: Home Assistant startad fullt ut.")

        # Lyssnaren har nu aktiverats. Ta bort dess avregistreringsfunktion från vår lista
        # för att förhindra att _remove_listeners försöker anropa den igen.
        # async_listen_once hanterar sin egen avregistrering från bussen.
        if self._event_start_listener_unsub_handle is not None:
            if self._event_start_listener_unsub_handle in self._listeners:
                try:
                    self._listeners.remove(self._event_start_listener_unsub_handle)
                    if self._debug_logging_enabled:
                        _LOGGER.debug(f"[{self._config_entry.title}] Tog bort EVENT_HOMEASSISTANT_START lyssnar-handle från self._listeners.")
                except ValueError:
                    if self._debug_logging_enabled: # Bör inte hända
                        _LOGGER.debug(f"[{self._config_entry.title}] EVENT_HOMEASSISTANT_START lyssnar-handle hittades ej i self._listeners vid borttagning.")
            self._event_start_listener_unsub_handle = None # Rensa vår referens

        await self._perform_initial_updates_and_control()

    async def async_will_remove_from_hass(self) -> None:
        if self._debug_logging_enabled:
            _LOGGER.debug(f"[{self._config_entry.title}] async_will_remove_from_hass: Tar bort lyssnare.")
        self._remove_listeners()
        await super().async_will_remove_from_hass()

    def _remove_listeners(self):
        """Tar bort alla registrerade lyssnare."""
        if self._debug_logging_enabled:
            _LOGGER.debug(f"[{self._config_entry.title}] _remove_listeners anropad. Antal lyssnare innan: {len(self._listeners)}")
        # Anropa avregistreringsfunktionen för varje lyssnare i listan
        # och töm sedan listan.
        for unsub in self._listeners:
            try:
                unsub()
            except Exception as e: # Försök att avregistrera alla även om en misslyckas
                _LOGGER.warning(f"[{self._config_entry.title}] Fel vid avregistrering av lyssnare: {e}")
        self._listeners.clear()
        if self._debug_logging_enabled:
            _LOGGER.debug(f"[{self._config_entry.title}] Alla lyssnare borttagna från self._listeners.")

        # Säkerställ att även den specifika start-lyssnaren hanteras om den inte redan är det
        # (Denna logik är nu primärt i _async_home_assistant_started och när komponenten tas bort helt)
        if self._event_start_listener_unsub_handle is not None:
            if self._debug_logging_enabled:
                _LOGGER.debug(f"[{self._config_entry.title}] Försöker explicit avregistrera _event_start_listener_unsub_handle om den finns kvar (bör ej hända om HA startat).")
            try:
                self._event_start_listener_unsub_handle()
            except Exception as e:
                 _LOGGER.warning(f"[{self._config_entry.title}] Fel vid explicit avregistrering av _event_start_listener_unsub_handle: {e}")
            self._event_start_listener_unsub_handle = None


    @callback
    async def _update_config_from_options(self):
        self._config_data = {**self._config_entry.data, **self._config_entry.options}
        new_debug_logging_enabled = self._config_entry.options.get(CONF_DEBUG_LOGGING, DEFAULT_DEBUG_LOGGING)
        if self._debug_logging_enabled != new_debug_logging_enabled:
            _LOGGER.info(f"[{self._config_entry.title}] Debug-loggning ändrad till: {new_debug_logging_enabled}")
            self._debug_logging_enabled = new_debug_logging_enabled

        if self._debug_logging_enabled:
            _LOGGER.debug(f"[{self._config_entry.title}] _update_config_from_options: Laddar om konfiguration från options.")
            _LOGGER.debug(f"[{self._config_entry.title}] Nya options som används: {self._config_entry.options}")
            _LOGGER.debug(f"[{self._config_entry.title}] Fullständig sammanslagen config_data: {self._config_data}")

        new_temp_sensor = self._config_entry.options.get(CONF_TEMP_SENSOR_ENTITY)
        new_heater_switch = self._config_entry.options.get(CONF_HEATER_SWITCH_ENTITY)
        listeners_need_reset = False

        if self._temp_sensor_entity_id != new_temp_sensor:
            _LOGGER.info(f"[{self._config_entry.title}] Temperatursensor ändrad från '{self._temp_sensor_entity_id}' till: '{new_temp_sensor}'")
            self._temp_sensor_entity_id = new_temp_sensor
            listeners_need_reset = True
        if self._heater_switch_entity_id != new_heater_switch:
            _LOGGER.info(f"[{self._config_entry.title}] Värmeswitch ändrad från '{self._heater_switch_entity_id}' till: '{new_heater_switch}'")
            self._heater_switch_entity_id = new_heater_switch
            listeners_need_reset = True

        self._hysteresis = self._config_entry.options.get(CONF_HYSTERESIS, DEFAULT_HYSTERESIS)
        new_master_enabled_option = self._config_entry.options.get(CONF_MASTER_ENABLED)

        if new_master_enabled_option is not None:
            target_hvac_mode = HVACMode.HEAT if new_master_enabled_option else HVACMode.OFF
            if self._attr_hvac_mode != target_hvac_mode:
                self._attr_hvac_mode = target_hvac_mode
                _LOGGER.info(f"[{self._config_entry.title}] HVAC-läge uppdaterat till {self._attr_hvac_mode} via options-ändring (master_enabled).")

        if listeners_need_reset:
            if self._debug_logging_enabled:
                _LOGGER.debug(f"[{self._config_entry.title}] Återställer sensorlyssnare pga options-ändring.")
            self._setup_sensor_listeners() # Detta anropar _remove_listeners() först
            if self.hass.is_running: await self._perform_initial_updates_and_control()

    @callback
    async def _async_options_updated(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        _LOGGER.info(f"[{self._config_entry.title}] _async_options_updated: Options har ändrats, applicerar.")
        await self._update_config_from_options()
        await self._control_heating()
        self.async_schedule_update_ha_state()
        if self._debug_logging_enabled:
             _LOGGER.debug(f"[{self._config_entry.title}] _async_options_updated slutförd. Debug nu: {self._debug_logging_enabled}")

    # ... (resten av climate.py är oförändrad från föregående version med 2.3.0-logik) ...
    # Se till att alla _LOGGER.debug är villkorade med self._debug_logging_enabled
    # Jag inkluderar resten för fullständighet och för att säkerställa att inga debug-anrop missas.

    @callback
    async def _async_temp_sensor_changed(self, event: Event) -> None:
        new_state: Optional[State] = event.data.get("new_state")
        if self._debug_logging_enabled:
            _LOGGER.debug(f"[{self._config_entry.title}] Tempsensor '{self._temp_sensor_entity_id}' ändrades: {new_state.state if new_state else 'None'}")
        if self._update_from_temp_sensor_state(new_state):
            await self._control_heating()
            self.async_schedule_update_ha_state()

    def _update_from_temp_sensor_state(self, state: Optional[State]) -> bool: # Synkron
        changed = False
        if state and state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            try:
                current_temp = float(state.state)
                if self._current_temp != current_temp:
                    self._current_temp = current_temp
                    if self._debug_logging_enabled:
                        _LOGGER.debug(f"[{self._config_entry.title}] Aktuell temperatur {self._current_temp}°C från {self._temp_sensor_entity_id}")
                    changed = True
            except ValueError:
                _LOGGER.warning(f"[{self._config_entry.title}] Kunde inte tolka temp från {self._temp_sensor_entity_id}: {state.state}")
                if self._current_temp is not None: changed = True
                self._current_temp = None
        elif self._current_temp is not None:
            _LOGGER.warning(f"[{self._config_entry.title}] Temperatursensor {self._temp_sensor_entity_id} otillgänglig eller okänt tillstånd ({state.state if state else 'None'}).")
            self._current_temp = None
            changed = True
        return changed

    @callback
    def _async_heater_switch_changed(self, event: Event) -> None:
        new_state_obj: Optional[State] = event.data.get("new_state")
        old_state_obj: Optional[State] = event.data.get("old_state")
        switch_state_new = new_state_obj.state if new_state_obj else "okänt (ingen ny state)"
        switch_state_old = old_state_obj.state if old_state_obj else "okänt (ingen gammal state)"

        if new_state_obj and old_state_obj and new_state_obj.state == old_state_obj.state:
            if self._debug_logging_enabled:
                _LOGGER.debug(f"[{self._config_entry.title}] Värmeswitch '{self._heater_switch_entity_id}' attribut ändrades, men tillstånd ('{switch_state_new}') oförändrat. Ignorerar för HVACAction-uppdatering.")
            return

        _LOGGER.info(f"[{self._config_entry.title}] Värmeswitch '{self._heater_switch_entity_id}' ändrades från '{switch_state_old}' till '{switch_state_new}'. Förbereder schemaläggning av HA-statusuppdatering för HVACAction.")
        try:
            self.async_schedule_update_ha_state()
            if self._debug_logging_enabled:
                _LOGGER.debug(f"[{self._config_entry.title}] async_schedule_update_ha_state ANROPAD från _async_heater_switch_changed.")
        except Exception as e:
            _LOGGER.error(f"[{self._config_entry.title}] FEL vid anrop av async_schedule_update_ha_state i _async_heater_switch_changed: {e}", exc_info=True)

    async def _control_heating(self) -> None:
        if self._attr_hvac_mode != HVACMode.HEAT:
            if self._debug_logging_enabled:
                _LOGGER.debug(f"[{self._config_entry.title}] HVAC-läge {self._attr_hvac_mode}, styr ej värme.")
            if self._heater_switch_entity_id:
                current_heater_state_obj = self.hass.states.get(self._heater_switch_entity_id)
                if current_heater_state_obj and current_heater_state_obj.state == "on":
                    _LOGGER.info(f"[{self._config_entry.title}] Termostat är AV (läge: {self._attr_hvac_mode}), stänger av värmare {self._heater_switch_entity_id}.")
                    await self._set_heater_state(False)
            return

        if self._current_temp is None or self._target_temp is None:
            if self._debug_logging_enabled:
                _LOGGER.debug(f"[{self._config_entry.title}] Aktuell temp ({self._current_temp}) eller måltemp ({self._target_temp}) okänd. Kan ej styra värme.")
            return

        if not self._heater_switch_entity_id:
            _LOGGER.warning(f"[{self._config_entry.title}] Ingen värmeswitch konfigurerad för styrning.")
            return

        heater_state_obj = self.hass.states.get(self._heater_switch_entity_id)
        if not heater_state_obj:
            _LOGGER.warning(f"[{self._config_entry.title}] Värmeswitch {self._heater_switch_entity_id} ej hittad i HA:s tillstånd. Kan ej styra.")
            return

        is_heater_on = heater_state_obj.state == "on"
        if self._debug_logging_enabled:
            _LOGGER.debug(f"[{self._config_entry.title}] Styrlogik: Akt: {self._current_temp}°C, Mål: {self._target_temp}°C, Hys: {self._hysteresis}°C, Värmare: {'PÅ' if is_heater_on else 'AV'}")

        lower_bound = self._target_temp - (self._hysteresis / 2)
        upper_bound = self._target_temp + (self._hysteresis / 2)
        desired_action_turn_on = None

        if is_heater_on:
            if self._current_temp >= upper_bound:
                if self._debug_logging_enabled:
                    _LOGGER.debug(f"[{self._config_entry.title}] Temp {self._current_temp}°C >= övre gräns {upper_bound}°C. Önskar stänga AV.")
                desired_action_turn_on = False
        else:
            if self._current_temp <= lower_bound:
                if self._debug_logging_enabled:
                    _LOGGER.debug(f"[{self._config_entry.title}] Temp {self._current_temp}°C <= nedre gräns {lower_bound}°C. Önskar slå PÅ.")
                desired_action_turn_on = True

        if desired_action_turn_on is True:
            _LOGGER.info(f"[{self._config_entry.title}] Värmaren är AV, men temperaturen ({self._current_temp}°C) är under eller lika med nedre gräns ({lower_bound}°C). Slår PÅ värmaren.")
            await self._set_heater_state(True)
        elif desired_action_turn_on is False:
            _LOGGER.info(f"[{self._config_entry.title}] Värmaren är PÅ, men temperaturen ({self._current_temp}°C) är över eller lika med övre gräns ({upper_bound}°C). Stänger AV värmaren.")
            await self._set_heater_state(False)
        else:
            if self._debug_logging_enabled:
                _LOGGER.debug(f"[{self._config_entry.title}] Värmarens nuvarande tillstånd ('{'PÅ' if is_heater_on else 'AV'}') matchar önskat tillstånd baserat på temp ({self._current_temp}°C) vs gränser ({lower_bound}°C-{upper_bound}°C). Ingen åtgärd.")

    async def _set_heater_state(self, turn_on: bool) -> None:
        if not self._heater_switch_entity_id:
            _LOGGER.warning(f"[{self._config_entry.title}] Ingen värmeswitch konfigurerad, kan inte ändra status.")
            return

        service_to_call = "turn_on" if turn_on else "turn_off"
        entity_id_to_call = self._heater_switch_entity_id
        current_state = self.hass.states.get(entity_id_to_call)

        if current_state and ((turn_on and current_state.state == "on") or (not turn_on and current_state.state == "off")):
            if self._debug_logging_enabled:
                _LOGGER.debug(f"[{self._config_entry.title}] Värmare '{entity_id_to_call}' är redan i önskat läge ('{current_state.state}'). Inget serviceanrop görs.")
            return

        _LOGGER.info(f"[{self._config_entry.title}] Anropar service switch.{service_to_call} för entitet '{entity_id_to_call}'.")
        try:
            await self.hass.services.async_call(
                "switch", service_to_call, {"entity_id": entity_id_to_call}, blocking=True, context=self._context
            )
            if self._debug_logging_enabled:
                _LOGGER.debug(f"[{self._config_entry.title}] Serviceanrop switch.{service_to_call} för '{entity_id_to_call}' slutfört.")
        except Exception as e:
            _LOGGER.error(f"[{self._config_entry.title}] FEL vid anrop till switch.{service_to_call} för '{entity_id_to_call}': {e}", exc_info=True)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if self._debug_logging_enabled:
            _LOGGER.debug(f"[{self._config_entry.title}] async_set_temperature anropad med: {kwargs}")

        if temperature is None:
            if self._debug_logging_enabled:
                _LOGGER.debug(f"[{self._config_entry.title}] Ingen temperatur angiven i async_set_temperature.")
            return

        new_target_temp = float(temperature)
        if new_target_temp == self._target_temp:
            if self._debug_logging_enabled:
                _LOGGER.debug(f"[{self._config_entry.title}] Måltemperatur redan {new_target_temp}°C, ingen ändring.")
            return

        self._target_temp = new_target_temp
        _LOGGER.info(f"[{self._config_entry.title}] Ny måltemperatur satt till {self._target_temp}°C.")
        await self._control_heating()
        self.async_write_ha_state()
        if self._debug_logging_enabled:
            _LOGGER.debug(f"[{self._config_entry.title}] async_write_ha_state anropad efter måltemperaturändring.")

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        if self._debug_logging_enabled:
            _LOGGER.debug(f"[{self._config_entry.title}] async_set_hvac_mode anropad med: {hvac_mode}")

        if hvac_mode not in self._attr_hvac_modes:
            _LOGGER.warning(f"[{self._config_entry.title}] HVAC-läge {hvac_mode} stöds ej. Tillgängliga: {self._attr_hvac_modes}")
            return

        if hvac_mode == self._attr_hvac_mode:
            if self._debug_logging_enabled:
                _LOGGER.debug(f"[{self._config_entry.title}] HVAC-läge redan {hvac_mode}, ingen ändring.")
            return

        _LOGGER.info(f"[{self._config_entry.title}] Sätter HVAC-läge till {hvac_mode}.")
        self._attr_hvac_mode = hvac_mode
        new_options = {**self._config_entry.options}
        new_options[CONF_MASTER_ENABLED] = (hvac_mode == HVACMode.HEAT)
        if self._debug_logging_enabled:
            _LOGGER.debug(f"[{self._config_entry.title}] Uppdaterar config_entry options med CONF_MASTER_ENABLED={new_options[CONF_MASTER_ENABLED]}")
        self.hass.config_entries.async_update_entry(self._config_entry, options=new_options)
        await self._control_heating()
        self.async_write_ha_state()
        if self._debug_logging_enabled:
            _LOGGER.debug(f"[{self._config_entry.title}] async_write_ha_state anropad efter HVAC-lägesändring.")

    async def async_turn_on(self) -> None:
        if self._debug_logging_enabled:
            _LOGGER.debug(f"[{self._config_entry.title}] async_turn_on anropad.")
        await self.async_set_hvac_mode(HVACMode.HEAT)

    async def async_turn_off(self) -> None:
        if self._debug_logging_enabled:
            _LOGGER.debug(f"[{self._config_entry.title}] async_turn_off anropad.")
        await self.async_set_hvac_mode(HVACMode.OFF)