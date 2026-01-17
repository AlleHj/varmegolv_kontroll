"""Testar config flow och options flow för Golvvärmekontroll."""
from unittest.mock import patch
import pytest
import voluptuous as vol

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.const import CONF_NAME

from custom_components.varmegolv_kontroll.const import (
    DOMAIN,
    CONF_TEMP_SENSOR_ENTITY,
    CONF_HEATER_SWITCH_ENTITY,
    CONF_HYSTERESIS,
    CONF_TARGET_TEMP,
    CONF_MASTER_ENABLED,
)

# Testdata
TEST_DATA = {
    CONF_NAME: "Golvvärmekontroll",
    CONF_TEMP_SENSOR_ENTITY: "sensor.badrum_temp",
    CONF_HEATER_SWITCH_ENTITY: "switch.golvvarme_aktor",
    CONF_HYSTERESIS: 0.5,
    CONF_TARGET_TEMP: 20.0,
    CONF_MASTER_ENABLED: True,
}

@pytest.mark.asyncio
async def test_config_flow_and_options_flow_persistence(hass: HomeAssistant) -> None:
    """
    Testar att:
    1. Vi kan konfigurera integrationen (User Flow).
    2. En ConfigEntry skapas med rätt data.
    3. Options Flow (kugghjulet) laddas utan krasch.
    4. Options Flow har formuläret förifyllt med våra tidigare värden.
    """

    # -------------------------------------------------------------------------
    # STEG 1: Initiera Config Flow
    # -------------------------------------------------------------------------
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    # -------------------------------------------------------------------------
    # STEG 2: Fyll i formuläret och bekräfta
    # -------------------------------------------------------------------------
    with patch(
        "custom_components.varmegolv_kontroll.async_setup_entry", return_value=True
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input=TEST_DATA,
        )
        await hass.async_block_till_done()

    assert result["type"] == FlowResultType.CREATE_ENTRY
    entry = result["result"]

    # -------------------------------------------------------------------------
    # STEG 3: Initiera Options Flow
    # -------------------------------------------------------------------------
    # Detta testar att din fix för AttributeError fungerar
    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"

    # -------------------------------------------------------------------------
    # STEG 4: Verifiera att fälten är förifyllda (Persistence check)
    # -------------------------------------------------------------------------
    schema = result["data_schema"]

    # Hämta defaults från schemat på korrekt sätt.
    # Voluptuous lagrar 'default' i Nyckeln (vol.Required), inte i Värdet (Selector).
    defaults = {}
    for key in schema.schema:
        # key.schema är namnet på fältet (sträng)
        # key.default är standardvärdet (eller en factory)
        value = key.default() if callable(key.default) else key.default
        if value is not vol.UNDEFINED:
            defaults[key.schema] = value

    # Nu kan vi jämföra
    assert defaults[CONF_TEMP_SENSOR_ENTITY] == TEST_DATA[CONF_TEMP_SENSOR_ENTITY]
    assert defaults[CONF_HEATER_SWITCH_ENTITY] == TEST_DATA[CONF_HEATER_SWITCH_ENTITY]
    assert defaults[CONF_HYSTERESIS] == TEST_DATA[CONF_HYSTERESIS]
    assert defaults[CONF_MASTER_ENABLED] == TEST_DATA[CONF_MASTER_ENABLED]