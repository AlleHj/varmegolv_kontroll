"""Globala fixtures för Golvvärmekontroll tester."""
import os
import sys
import pytest
from homeassistant import loader

# -------------------------------------------------------------------
# PATCH: Lägg till sökvägar för att hitta 'custom_components'
# -------------------------------------------------------------------
# Detta säkerställer att vi kan importera 'custom_components.varmegolv_kontroll'
# oavsett varifrån vi kör 'pytest'-kommandot.
# Vi går upp två nivåer från denna fil (tests -> varmegolv_kontroll -> custom_components -> ROOT)
# OBS: Justera antalet 'dirname' beroende på din exakta mappstruktur.
# Om strukturen är: config/custom_components/varmegolv_kontroll/tests/conftest.py
# Behöver vi gå upp till 'config' mappen.

# Hämta mappen där denna fil ligger
file_dir = os.path.dirname(__file__)

# Gå upp till roten (där 'custom_components' mappen ligger)
# Nivå 1: .../varmegolv_kontroll/tests
# Nivå 2: .../varmegolv_kontroll
# Nivå 3: .../custom_components
# Nivå 4: .../config (HÄR vill vi vara för att importen ska funka)
root_dir = os.path.abspath(os.path.join(file_dir, "..", "..", ".."))

# Lägg till roten i sys.path
sys.path.insert(0, root_dir)

@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(hass, enable_custom_integrations):
    """Aktiverar custom integrations automatiskt för alla tester.

    Detta är nödvändigt för att pytest-homeassistant-custom-component
    ska tillåta att integrationen laddas under testning.
    """
    # Detta löser problemet med "AttributeError: 'async_generator' object has no attribute 'data'"
    # eller att gammal kod ligger kvar i minnet, genom att rensa cachen
    # så Home Assistant tvingas ladda din integration på nytt.
    if loader.DATA_CUSTOM_COMPONENTS in hass.data:
        hass.data.pop(loader.DATA_CUSTOM_COMPONENTS)
    yield