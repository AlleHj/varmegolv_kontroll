# Home Assistant Anpassad Golvvärmekontroll (varmegolv_kontroll)

Detta är en anpassad komponent (custom component) för Home Assistant som tillhandahåller en termostatfunktion för att styra elektrisk golvvärme eller liknande värmesystem. Den använder en angiven temperatursensor och en switch-entitet för att reglera värmen.

**Aktuell version:** `2.3.2` (2025-05-28)

## Funktioner
(... oförändrad ...)

## Installation
(... oförändrad ...)

## Konfiguration
(... oförändrad ...)

## Användning
(... oförändrad ...)

## Bidra
(... oförändrad ...)

## Ändringslogg

### Version 2.3.2 (2025-05-28)
* **FÖRBÄTTRING:** Justerat loggningsnivåer i `climate.py`. Flera tidigare `INFO`-loggar är nu `DEBUG`-loggar och styrs av debug-checkboxen. Kritiska meddelanden om konfigurationsändringar, användarinitierade tillståndsändringar och de specifika meddelandena när värmaren aktivt slås på/av eller styrs är kvar som `INFO`. Detta minskar mängden `INFO`-loggar vid normal drift utan debug aktiverat.

### Version 2.3.1 (2025-05-28)
* **FIX:** Korrigerad hantering av `EVENT_HOMEASSISTANT_START`-lyssnaren i `climate.py` för att förhindra `ValueError` vid avregistrering efter att lyssnaren redan har aktiverats. Detta löser ett problem där avregistreringsanropet misslyckades om det skedde efter att Home Assistant startat och lyssnaren redan hade kört och avregistrerats automatiskt.
* **FÖRBÄTTRING:** `HELP_URL` i `config_flow.py` uppdaterad för att peka på `HELP_sv.md` i roten av GitHub-repot. Länken i `README.md` till `HELP_sv.md` är också uppdaterad.

(... resten av ändringsloggen från tidigare ...)

