"""Climate-plattform för Golvvärmekontroll.

2025-05-28 2.3.6
"""

import logging
from collections.abc import Callable
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_TEMPERATURE,
    EVENT_HOMEASSISTANT_START,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import Event, HomeAssistant, State, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    CONF_DEBUG_LOGGING,
    CONF_HEATER_SWITCH_ENTITY,
    CONF_HYSTERESIS,
    CONF_MASTER_ENABLED,
    CONF_TARGET_TEMP,
    CONF_TEMP_SENSOR_ENTITY,
    DEFAULT_DEBUG_LOGGING,
    DEFAULT_HYSTERESIS,
    DEFAULT_TARGET_TEMP,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Sätt upp climate-entiteten från en config entry."""
    _LOGGER.info(
        "Sätter upp climate-entitet för '%s' (%s) v%s",
        config_entry.title,
        config_entry.entry_id,
        config_entry.version,
    )
    initial_config_data = {**config_entry.data, **config_entry.options}
    controller = VarmegolvClimate(hass, config_entry, initial_config_data)
    async_add_entities([controller], True)


class VarmegolvClimate(ClimateEntity, RestoreEntity):
    """Representerar en Golvvärmekontroll termostat."""

    _attr_has_entity_name = True
    _attr_name = None

    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )
    _attr_fan_mode: str | None = None
    _attr_fan_modes: list[str] | None = None
    _attr_preset_mode: str | None = None
    _attr_preset_modes: list[str] | None = None
    _attr_swing_mode: str | None = None
    _attr_swing_modes: list[str] | None = None
    _attr_target_humidity: float | None = None

    def __init__(
        self, hass: HomeAssistant, config_entry: ConfigEntry, config_data: dict
    ) -> None:
        """Initialisera termostaten."""
        self.hass = hass
        self._config_entry = config_entry
        self._config_data = dict(config_data)
        self._temp_sensor_entity_id = self._config_data.get(CONF_TEMP_SENSOR_ENTITY)
        self._heater_switch_entity_id = self._config_data.get(CONF_HEATER_SWITCH_ENTITY)
        self._hysteresis = self._config_data.get(CONF_HYSTERESIS, DEFAULT_HYSTERESIS)
        self._debug_logging_enabled = self._config_data.get(
            CONF_DEBUG_LOGGING, DEFAULT_DEBUG_LOGGING
        )

        self._attr_unique_id = f"{config_entry.entry_id}_thermostat"
        self._attr_temperature_unit = hass.config.units.temperature_unit
        self._current_temp: float | None = None
        self._target_temp: float = self._config_data.get(
            CONF_TARGET_TEMP, DEFAULT_TARGET_TEMP
        )
        initial_master_enabled = self._config_data.get(CONF_MASTER_ENABLED, True)
        self._attr_hvac_mode: HVACMode = (
            HVACMode.HEAT if initial_master_enabled else HVACMode.OFF
        )
        self._attr_hvac_action: HVACAction | None = None
        self._listeners: list[Callable[[], None]] = []
        self._event_start_listener_unsub_handle: Callable[[], None] | None = None

        if self._debug_logging_enabled:
            _LOGGER.debug(
                "[%s] __init__: TargetTemp=%s, HVACMode=%s, DebugLog=%s",
                self._config_entry.title,
                self._target_temp,
                self._attr_hvac_mode,
                self._debug_logging_enabled,
            )

    @property
    def device_info(self) -> dict[str, Any]:
        """Returnera enhetsinformation för enheten."""
        return {
            "identifiers": {(DOMAIN, self._config_entry.entry_id)},
            "name": self._config_entry.title,
            "manufacturer": "Anpassad Komponent AB (AlleHj)",
            "model": "Golvvärmetermostat",
            "sw_version": self._config_entry.version,
        }

    @property
    def current_temperature(self) -> float | None:
        """Returnera aktuell temperatur."""
        return self._current_temp

    @property
    def target_temperature(self) -> float | None:
        """Returnera inställd måltemperatur."""
        return self._target_temp

    @property
    def hvac_mode(self) -> HVACMode:
        """Returnera aktuellt HVAC-läge."""
        return self._attr_hvac_mode

    @property
    def hvac_action(self) -> HVACAction | None:
        """Returnera aktuell HVAC-åtgärd (heating, idle, off)."""
        if self._attr_hvac_mode == HVACMode.OFF:
            return HVACAction.OFF
        if self._heater_switch_entity_id:
            heater_state = self.hass.states.get(self._heater_switch_entity_id)
            if heater_state and heater_state.state == "on":
                return HVACAction.HEATING
        return HVACAction.IDLE

    async def async_added_to_hass(self) -> None:
        """Körs när entiteten läggs till i Home Assistant."""
        await super().async_added_to_hass()
        if self._debug_logging_enabled:
            _LOGGER.debug(
                "[%s] async_added_to_hass: Startar.", self._config_entry.title
            )

        initial_target_temp_from_data = self._config_entry.data.get(
            CONF_TARGET_TEMP, DEFAULT_TARGET_TEMP
        )
        initial_master_enabled_from_data = self._config_entry.data.get(
            CONF_MASTER_ENABLED, True
        )
        initial_master_enabled_from_options = self._config_entry.options.get(
            CONF_MASTER_ENABLED, initial_master_enabled_from_data
        )

        last_state = await self.async_get_last_state()
        if last_state:
            if self._debug_logging_enabled:
                _LOGGER.debug(
                    "[%s] Återställer från last_state: %s",
                    self._config_entry.title,
                    last_state.attributes,
                )
            self._target_temp = float(
                last_state.attributes.get(
                    ATTR_TEMPERATURE, initial_target_temp_from_data
                )
            )
            restored_hvac_mode_str = last_state.attributes.get("hvac_mode")
            if restored_hvac_mode_str:
                try:
                    self._attr_hvac_mode = HVACMode(restored_hvac_mode_str)
                except ValueError:
                    _LOGGER.warning(
                        "[%s] Ogiltigt HVAC-läge '%s' återställt, "
                        "använder från config (options/data).",
                        self._config_entry.title,
                        restored_hvac_mode_str,
                    )
                    self._attr_hvac_mode = (
                        HVACMode.HEAT
                        if initial_master_enabled_from_options
                        else HVACMode.OFF
                    )
            else:
                if self._debug_logging_enabled:
                    _LOGGER.debug(
                        "[%s] Inget HVAC-läge i last_state, "
                        "använder från config (options/data).",
                        self._config_entry.title,
                    )
                self._attr_hvac_mode = (
                    HVACMode.HEAT
                    if initial_master_enabled_from_options
                    else HVACMode.OFF
                )
        else:
            if self._debug_logging_enabled:
                _LOGGER.debug(
                    "[%s] Inget last_state, "
                    "använder initiala konfigurationsvärden (data/options).",
                    self._config_entry.title,
                )
            self._target_temp = initial_target_temp_from_data
            self._attr_hvac_mode = (
                HVACMode.HEAT if initial_master_enabled_from_options else HVACMode.OFF
            )

        if self._debug_logging_enabled:
            _LOGGER.debug(
                "[%s] Efter återställning/init: TargetTemp=%s, HVACMode=%s",
                self._config_entry.title,
                self._target_temp,
                self._attr_hvac_mode,
            )

        self._config_entry.async_on_unload(
            self._config_entry.add_update_listener(
                self._async_options_updated_listener_proxy
            )
        )

        if not self.hass.is_running:
            if self._debug_logging_enabled:
                _LOGGER.debug(
                    "[%s] HA ej startat, reg. EVENT_HOMEASSISTANT_START listener.",
                    self._config_entry.title,
                )
            self._event_start_listener_unsub_handle = self.hass.bus.async_listen_once(
                EVENT_HOMEASSISTANT_START, self._async_home_assistant_started
            )
            self._listeners.append(self._event_start_listener_unsub_handle)
        else:
            if self._debug_logging_enabled:
                _LOGGER.debug(
                    "[%s] HA körs, anropar _perform_initial_updates_and_control direkt.",
                    self._config_entry.title,
                )
            await self._perform_initial_updates_and_control()

        self._setup_sensor_listeners()

    async def _async_options_updated_listener_proxy(
        self, hass: HomeAssistant, entry: ConfigEntry
    ) -> None:
        """Proxy för att logga anrop till options-lyssnaren."""
        if self._debug_logging_enabled:
            _LOGGER.debug(
                "[%s] Options update listener proxy anropad. Debug innan uppdatering: %s",
                self._config_entry.title,
                self._debug_logging_enabled,
            )
        await self._async_options_updated(hass, entry)

    async def _perform_initial_updates_and_control(self) -> None:
        """Utför initiala uppdateringar och värmestyrning."""
        if self._debug_logging_enabled:
            _LOGGER.debug(
                "[%s] _perform_initial_updates_and_control anropad.",
                self._config_entry.title,
            )
        if self._temp_sensor_entity_id:
            temp_sensor_state = self.hass.states.get(self._temp_sensor_entity_id)
            if temp_sensor_state:
                self._update_from_temp_sensor_state(temp_sensor_state)
        await self._control_heating()
        self.async_schedule_update_ha_state(True)

    def _setup_sensor_listeners(self) -> None:
        """Sätt upp lyssnare för sensorer och switchar."""
        if self._debug_logging_enabled:
            _LOGGER.debug(
                "[%s] Sätter upp sensorlyssnare (rensa gamla först).",
                self._config_entry.title,
            )
        self._remove_listeners()

        if self._temp_sensor_entity_id:
            unsub = async_track_state_change_event(
                self.hass, self._temp_sensor_entity_id, self._async_temp_sensor_changed
            )
            self._listeners.append(unsub)
            if self._debug_logging_enabled:
                _LOGGER.debug(
                    "[%s] Lade till lyssnare för tempsensor: %s",
                    self._config_entry.title,
                    self._temp_sensor_entity_id,
                )

        if self._heater_switch_entity_id:
            unsub = async_track_state_change_event(
                self.hass,
                self._heater_switch_entity_id,
                self._async_heater_switch_changed,
            )
            self._listeners.append(unsub)
            if self._debug_logging_enabled:
                _LOGGER.debug(
                    "[%s] Lade till lyssnare för värmeswitch: %s",
                    self._config_entry.title,
                    self._heater_switch_entity_id,
                )

    async def _async_home_assistant_started(
        self, _event: Event
    ) -> None:  # Argument _event markerat som oanvänt
        """Körs när Home Assistant har startat fullt ut."""
        if self._debug_logging_enabled:
            _LOGGER.debug(
                "[%s] Event: Home Assistant startad fullt ut.", self._config_entry.title
            )

        if self._event_start_listener_unsub_handle is not None:
            if self._event_start_listener_unsub_handle in self._listeners:
                try:
                    self._listeners.remove(self._event_start_listener_unsub_handle)
                    if self._debug_logging_enabled:
                        _LOGGER.debug(
                            "[%s] Tog bort EVENT_HOMEASSISTANT_START "
                            "lyssnar-handle från self._listeners.",
                            self._config_entry.title,
                        )
                except ValueError:
                    if self._debug_logging_enabled:
                        _LOGGER.debug(
                            "[%s] EVENT_HOMEASSISTANT_START lyssnar-handle "
                            "hittades ej i self._listeners vid borttagning.",
                            self._config_entry.title,
                        )
            self._event_start_listener_unsub_handle = None

        await self._perform_initial_updates_and_control()

    async def async_will_remove_from_hass(self) -> None:
        """Körs när entiteten tas bort från Home Assistant."""
        if self._debug_logging_enabled:
            _LOGGER.debug(
                "[%s] async_will_remove_from_hass: Tar bort lyssnare.",
                self._config_entry.title,
            )
        self._remove_listeners()
        await super().async_will_remove_from_hass()

    def _remove_listeners(self) -> None:
        """Tar bort alla registrerade lyssnare."""
        if self._debug_logging_enabled:
            _LOGGER.debug(
                "[%s] _remove_listeners anropad. Antal lyssnare innan: %d",
                self._config_entry.title,
                len(self._listeners),
            )
        for unsub in self._listeners:
            try:
                unsub()
            except Exception:  # Behåller bred Exception här för robusthet
                _LOGGER.exception(
                    "[%s] Fel vid avregistrering av lyssnare.", self._config_entry.title
                )
        self._listeners.clear()
        if self._debug_logging_enabled:
            _LOGGER.debug(
                "[%s] Alla lyssnare borttagna från self._listeners.",
                self._config_entry.title,
            )

        if self._event_start_listener_unsub_handle is not None:
            if self._debug_logging_enabled:
                _LOGGER.debug(
                    "[%s] Försöker explicit avregistrera "
                    "_event_start_listener_unsub_handle om den finns kvar.",
                    self._config_entry.title,
                )
            try:
                self._event_start_listener_unsub_handle()
            except Exception:  # Behåller bred Exception här
                _LOGGER.exception(
                    "[%s] Fel vid explicit avregistrering av _event_start_listener_unsub_handle.",
                    self._config_entry.title,
                )
            self._event_start_listener_unsub_handle = None

    @callback
    async def _update_config_from_options(self) -> None:
        """Uppdaterar intern konfiguration baserat på ändrade options."""
        self._config_data = {**self._config_entry.data, **self._config_entry.options}
        new_debug_logging_enabled = self._config_entry.options.get(
            CONF_DEBUG_LOGGING, DEFAULT_DEBUG_LOGGING
        )
        if self._debug_logging_enabled != new_debug_logging_enabled:
            _LOGGER.info(
                "[%s] Debug-loggning ändrad till: %s",
                self._config_entry.title,
                new_debug_logging_enabled,
            )
            self._debug_logging_enabled = new_debug_logging_enabled

        if self._debug_logging_enabled:
            _LOGGER.debug(
                "[%s] _update_config_from_options: Laddar om konfiguration från options.",
                self._config_entry.title,
            )
            _LOGGER.debug(
                "[%s] Nya options som används: %s",
                self._config_entry.title,
                self._config_entry.options,
            )
            _LOGGER.debug(
                "[%s] Fullständig sammanslagen config_data: %s",
                self._config_entry.title,
                self._config_data,
            )

        new_temp_sensor = self._config_entry.options.get(CONF_TEMP_SENSOR_ENTITY)
        new_heater_switch = self._config_entry.options.get(CONF_HEATER_SWITCH_ENTITY)
        listeners_need_reset = False

        if self._temp_sensor_entity_id != new_temp_sensor:
            _LOGGER.info(
                "[%s] Temperatursensor ändrad från '%s' till: '%s'",
                self._config_entry.title,
                self._temp_sensor_entity_id,
                new_temp_sensor,
            )
            self._temp_sensor_entity_id = new_temp_sensor
            listeners_need_reset = True
        if self._heater_switch_entity_id != new_heater_switch:
            _LOGGER.info(
                "[%s] Värmeswitch ändrad från '%s' till: '%s'",
                self._config_entry.title,
                self._heater_switch_entity_id,
                new_heater_switch,
            )
            self._heater_switch_entity_id = new_heater_switch
            listeners_need_reset = True

        self._hysteresis = self._config_entry.options.get(
            CONF_HYSTERESIS, DEFAULT_HYSTERESIS
        )
        new_master_enabled_option = self._config_entry.options.get(CONF_MASTER_ENABLED)

        if new_master_enabled_option is not None:
            target_hvac_mode = (
                HVACMode.HEAT if new_master_enabled_option else HVACMode.OFF
            )
            if self._attr_hvac_mode != target_hvac_mode:
                _LOGGER.info(
                    "[%s] HVAC-läge uppdaterat till %s "
                    "via options-ändring (master_enabled).",
                    self._config_entry.title,
                    target_hvac_mode,
                )
                self._attr_hvac_mode = target_hvac_mode

        if listeners_need_reset:
            if self._debug_logging_enabled:
                _LOGGER.debug(
                    "[%s] Återställer sensorlyssnare pga options-ändring.",
                    self._config_entry.title,
                )
            self._setup_sensor_listeners()
            if self.hass.is_running:
                await self._perform_initial_updates_and_control()

    @callback
    async def _async_options_updated(
        self, hass: HomeAssistant, entry: ConfigEntry
    ) -> None:
        """Hanterar uppdateringar av options för en config entry."""
        if self._debug_logging_enabled:
            _LOGGER.debug(
                "[%s] _async_options_updated: Options har ändrats, applicerar.",
                self._config_entry.title,
            )
        await self._update_config_from_options()
        await self._control_heating()
        self.async_schedule_update_ha_state()
        if self._debug_logging_enabled:
            _LOGGER.debug(
                "[%s] _async_options_updated slutförd. Debug nu: %s",
                self._config_entry.title,
                self._debug_logging_enabled,
            )

    @callback
    async def _async_temp_sensor_changed(self, event: Event) -> None:
        """Hanterar ändringar av temperatursensorns tillstånd."""
        new_state: State | None = event.data.get("new_state")
        if self._debug_logging_enabled:
            _LOGGER.debug(
                "[%s] Tempsensor '%s' ändrades: %s",
                self._config_entry.title,
                self._temp_sensor_entity_id,
                new_state.state if new_state else "None",
            )
        if self._update_from_temp_sensor_state(new_state):
            await self._control_heating()
            self.async_schedule_update_ha_state()

    def _update_from_temp_sensor_state(self, state: State | None) -> bool:
        """Uppdaterar intern temperatur från sensorns tillstånd. Returnerar True om ändring skett."""
        changed = False
        if state and state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            try:
                current_temp = float(state.state)
                if self._current_temp != current_temp:
                    self._current_temp = current_temp
                    if self._debug_logging_enabled:
                        _LOGGER.debug(
                            "[%s] Aktuell temperatur %.1f°C från %s",
                            self._config_entry.title,
                            self._current_temp,
                            self._temp_sensor_entity_id,
                        )
                    changed = True
            except ValueError:
                _LOGGER.warning(
                    "[%s] Kunde inte tolka temp från %s: %s",
                    self._config_entry.title,
                    self._temp_sensor_entity_id,
                    state.state,
                )
                if self._current_temp is not None:
                    changed = True
                self._current_temp = None
        elif self._current_temp is not None:
            _LOGGER.warning(
                "[%s] Temperatursensor %s otillgänglig eller okänt tillstånd (%s).",
                self._config_entry.title,
                self._temp_sensor_entity_id,
                state.state if state else "None",
            )
            self._current_temp = None
            changed = True
        return changed

    @callback
    def _async_heater_switch_changed(self, event: Event) -> None:
        """Hanterar ändringar av värmeswitchens tillstånd."""
        new_state_obj: State | None = event.data.get("new_state")
        old_state_obj: State | None = event.data.get("old_state")
        switch_state_new = (
            new_state_obj.state if new_state_obj else "okänt (ingen ny state)"
        )
        switch_state_old = (
            old_state_obj.state if old_state_obj else "okänt (ingen gammal state)"
        )

        if (
            new_state_obj
            and old_state_obj
            and new_state_obj.state == old_state_obj.state
        ):
            if self._debug_logging_enabled:
                _LOGGER.debug(
                    "[%s] Värmeswitch '%s' attribut ändrades, "
                    "men tillstånd ('%s') oförändrat. Ignorerar.",
                    self._config_entry.title,
                    self._heater_switch_entity_id,
                    switch_state_new,
                )
            return

        if self._debug_logging_enabled:
            _LOGGER.debug(
                "[%s] Värmeswitch '%s' ändrades från '%s' till '%s'. "
                "Schemalägger HA-statusuppdatering.",
                self._config_entry.title,
                self._heater_switch_entity_id,
                switch_state_old,
                switch_state_new,
            )
        try:
            self.async_schedule_update_ha_state()
            if self._debug_logging_enabled:
                _LOGGER.debug(
                    "[%s] async_schedule_update_ha_state ANROPAD "
                    "från _async_heater_switch_changed.",
                    self._config_entry.title,
                )
        except Exception:
            _LOGGER.exception(
                "[%s] FEL vid anrop av async_schedule_update_ha_state "
                "i _async_heater_switch_changed.",
                self._config_entry.title,
            )

    async def _control_heating(self) -> None:
        """Styr värmeelementet baserat på temperatur och inställningar."""
        if self._attr_hvac_mode != HVACMode.HEAT:
            if self._debug_logging_enabled:
                _LOGGER.debug(
                    "[%s] HVAC-läge %s, styr ej värme.",
                    self._config_entry.title,
                    self._attr_hvac_mode,
                )
            if self._heater_switch_entity_id:
                current_heater_state_obj = self.hass.states.get(
                    self._heater_switch_entity_id
                )
                if current_heater_state_obj and current_heater_state_obj.state == "on":
                    _LOGGER.info(
                        "[%s] Termostat är AV (läge: %s), stänger av värmare %s.",
                        self._config_entry.title,
                        self._attr_hvac_mode,
                        self._heater_switch_entity_id,
                    )
                    await self._set_heater_state(False)
            return

        if self._current_temp is None or self._target_temp is None:
            if self._debug_logging_enabled:
                _LOGGER.debug(
                    "[%s] Aktuell temp (%s) eller måltemp (%s) okänd. Kan ej styra värme.",
                    self._config_entry.title,
                    self._current_temp,
                    self._target_temp,
                )
            return

        if not self._heater_switch_entity_id:
            _LOGGER.warning(
                "[%s] Ingen värmeswitch konfigurerad för styrning.",
                self._config_entry.title,
            )
            return

        heater_state_obj = self.hass.states.get(self._heater_switch_entity_id)
        if not heater_state_obj:
            _LOGGER.warning(
                "[%s] Värmeswitch %s ej hittad i HA:s tillstånd. Kan ej styra.",
                self._config_entry.title,
                self._heater_switch_entity_id,
            )
            return

        is_heater_on = heater_state_obj.state == "on"
        if self._debug_logging_enabled:
            _LOGGER.debug(
                "[%s] Styrlogik: Akt: %.1f°C, Mål: %.1f°C, Hys: %.1f°C, Värmare: %s",
                self._config_entry.title,
                self._current_temp or -99.9,
                self._target_temp or -99.9,
                self._hysteresis,
                "PÅ" if is_heater_on else "AV",
            )

        # Förutsätter att self._target_temp och self._current_temp inte är None här
        # baserat på tidigare kontroller.
        lower_bound = self._target_temp - (self._hysteresis / 2)
        upper_bound = self._target_temp + (self._hysteresis / 2)
        desired_action_turn_on: bool | None = None

        if is_heater_on:
            if self._current_temp >= upper_bound:
                if self._debug_logging_enabled:
                    _LOGGER.debug(
                        "[%s] Temp %.1f°C >= övre gräns %.1f°C. Önskar stänga AV.",
                        self._config_entry.title,
                        self._current_temp,
                        upper_bound,
                    )
                desired_action_turn_on = False
        elif self._current_temp <= lower_bound:  # Använder elif här
            if self._debug_logging_enabled:
                _LOGGER.debug(
                    "[%s] Temp %.1f°C <= nedre gräns %.1f°C. Önskar slå PÅ.",
                    self._config_entry.title,
                    self._current_temp,
                    lower_bound,
                )
            desired_action_turn_on = True

        if desired_action_turn_on is True:
            _LOGGER.info(
                "[%s] Värmaren är AV, men temperaturen (%.1f°C) är under eller lika "
                "med nedre gräns (%.1f°C). Slår PÅ värmaren.",
                self._config_entry.title,
                self._current_temp,
                lower_bound,
            )
            await self._set_heater_state(True)
        elif desired_action_turn_on is False:
            _LOGGER.info(
                "[%s] Värmaren är PÅ, men temperaturen (%.1f°C) är över eller lika "
                "med övre gräns (%.1f°C). Stänger AV värmaren.",
                self._config_entry.title,
                self._current_temp,
                upper_bound,
            )
            await self._set_heater_state(False)
        elif self._debug_logging_enabled:
            _LOGGER.debug(
                "[%s] Värmarens nuvarande tillstånd ('%s') matchar önskat tillstånd "
                "baserat på temp (%.1f°C) vs gränser (%.1f°C-%.1f°C). Ingen åtgärd.",
                self._config_entry.title,
                "PÅ" if is_heater_on else "AV",
                self._current_temp or -99.9,
                lower_bound,
                upper_bound,
            )

    async def _set_heater_state(self, turn_on: bool) -> None:
        """Sätter värmeelementets tillstånd (på/av)."""
        if not self._heater_switch_entity_id:
            _LOGGER.warning(
                "[%s] Ingen värmeswitch konfigurerad, kan inte ändra status.",
                self._config_entry.title,
            )
            return

        service_to_call = "turn_on" if turn_on else "turn_off"
        entity_id_to_call = self._heater_switch_entity_id
        current_state = self.hass.states.get(entity_id_to_call)

        if current_state and (
            (turn_on and current_state.state == "on")
            or (not turn_on and current_state.state == "off")
        ):
            if self._debug_logging_enabled:
                _LOGGER.debug(
                    "[%s] Värmare '%s' är redan i önskat läge ('%s'). "
                    "Inget serviceanrop görs.",
                    self._config_entry.title,
                    entity_id_to_call,
                    current_state.state,
                )
            return

        _LOGGER.info(
            "[%s] Anropar service switch.%s för entitet '%s'.",
            self._config_entry.title,
            service_to_call,
            entity_id_to_call,
        )
        try:
            await self.hass.services.async_call(
                "switch",
                service_to_call,
                {"entity_id": entity_id_to_call},
                blocking=True,
                context=self._context,
            )
            if self._debug_logging_enabled:
                _LOGGER.debug(
                    "[%s] Serviceanrop switch.%s för '%s' slutfört.",
                    self._config_entry.title,
                    service_to_call,
                    entity_id_to_call,
                )
        except Exception:
            _LOGGER.exception(
                "[%s] FEL vid anrop till switch.%s för '%s'.",
                self._config_entry.title,
                service_to_call,
                entity_id_to_call,
            )

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Sätt ny måltemperatur."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if self._debug_logging_enabled:
            _LOGGER.debug(
                "[%s] async_set_temperature anropad med: %s",
                self._config_entry.title,
                kwargs,
            )

        if temperature is None:
            if self._debug_logging_enabled:
                _LOGGER.debug(
                    "[%s] Ingen temperatur angiven i async_set_temperature.",
                    self._config_entry.title,
                )
            return

        new_target_temp = float(temperature)
        if new_target_temp == self._target_temp:
            if self._debug_logging_enabled:
                _LOGGER.debug(
                    "[%s] Måltemperatur redan %.1f°C, ingen ändring.",
                    self._config_entry.title,
                    new_target_temp,
                )
            return

        self._target_temp = new_target_temp
        _LOGGER.info(
            "[%s] Ny måltemperatur satt till %.1f°C.",
            self._config_entry.title,
            self._target_temp,
        )
        await self._control_heating()
        self.async_write_ha_state()
        if self._debug_logging_enabled:
            _LOGGER.debug(
                "[%s] async_write_ha_state anropad efter måltemperaturändring.",
                self._config_entry.title,
            )

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Sätt nytt HVAC-läge."""
        if self._debug_logging_enabled:
            _LOGGER.debug(
                "[%s] async_set_hvac_mode anropad med: %s",
                self._config_entry.title,
                hvac_mode,
            )

        if hvac_mode not in self._attr_hvac_modes:
            _LOGGER.warning(
                "[%s] HVAC-läge %s stöds ej. Tillgängliga: %s",
                self._config_entry.title,
                hvac_mode,
                self._attr_hvac_modes,
            )
            return

        if hvac_mode == self._attr_hvac_mode:
            if self._debug_logging_enabled:
                _LOGGER.debug(
                    "[%s] HVAC-läge redan %s, ingen ändring.",
                    self._config_entry.title,
                    hvac_mode,
                )
            return

        _LOGGER.info(
            "[%s] Sätter HVAC-läge till %s.", self._config_entry.title, hvac_mode
        )
        self._attr_hvac_mode = hvac_mode
        new_options = {**self._config_entry.options}
        new_options[CONF_MASTER_ENABLED] = hvac_mode == HVACMode.HEAT
        if self._debug_logging_enabled:
            _LOGGER.debug(
                "[%s] Uppdaterar config_entry options med CONF_MASTER_ENABLED=%s",
                self._config_entry.title,
                new_options[CONF_MASTER_ENABLED],
            )
        self.hass.config_entries.async_update_entry(
            self._config_entry, options=new_options
        )
        await self._control_heating()
        self.async_write_ha_state()
        if self._debug_logging_enabled:
            _LOGGER.debug(
                "[%s] async_write_ha_state anropad efter HVAC-lägesändring.",
                self._config_entry.title,
            )

    async def async_turn_on(self) -> None:
        """Slå på termostaten (sätt HVAC-läge till HEAT)."""
        if self._debug_logging_enabled:
            _LOGGER.debug("[%s] async_turn_on anropad.", self._config_entry.title)
        await self.async_set_hvac_mode(HVACMode.HEAT)

    async def async_turn_off(self) -> None:
        """Slå av termostaten (sätt HVAC-läge till OFF)."""
        if self._debug_logging_enabled:
            _LOGGER.debug("[%s] async_turn_off anropad.", self._config_entry.title)
        await self.async_set_hvac_mode(HVACMode.OFF)

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Denna funktion (set_fan_mode) stöds inte."""

    async def async_set_humidity(self, humidity: int) -> None:
        """Denna funktion (set_humidity) stöds inte."""

    async def async_set_preset_mode(
        self, preset_mode: str | None
    ) -> None:  # Lade till | None för att matcha basklass
        """Denna funktion (set_preset_mode) stöds inte."""

    async def async_set_swing_mode(self, swing_mode: str) -> None:
        """Denna funktion (set_swing_mode) stöds inte."""
