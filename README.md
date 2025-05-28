# Home Assistant Anpassad Golvvärmekontroll (varmegolv_kontroll)

Detta är en anpassad komponent (custom component) för Home Assistant som tillhandahåller en termostatfunktion för att styra elektrisk golvvärme eller liknande värmesystem. Den använder en angiven temperatursensor och en switch-entitet för att reglera värmen.

**Aktuell version:** `2.3.4` (2025-05-28)

## Funktioner

* Skapar en `climate`-entitet i Home Assistant.
* Använder en extern temperatursensor för avläsning av aktuell temperatur.
* Styr en extern switch-entitet (på/av) för att hantera värmeelementet.
* Justerbar måltemperatur.
* Konfigurerbar hysteres för att förhindra frekventa på/av-slag.
* HVAC-lägen: `HEAT` och `OFF`.
* Stöd för flera instanser (t.ex. en termostat per rum/zon).
* All konfiguration sker via Home Assistants användargränssnitt (Config Flow).
* Beständiga inställningar (måltemperatur och HVAC-läge sparas över omstarter).
* Dynamiskt aktiverbar debug-loggning per termostatinstans.
* Svenska översättningar för konfigurationsgränssnittet.
* Detaljerad [hjälpfil (HELP_sv.md)](HELP_sv.md) tillgänglig (ska finnas i roten av repot).

## Installation

Installationsinstruktioner och fullständig dokumentation finns i [**HELP_sv.md**](HELP_sv.md).

## Konfiguration

All konfiguration sker via Home Assistants användargränssnitt. Efter installation, gå till:
**Inställningar -> Enheter & Tjänster -> Lägg till Integration -> Sök efter "Golvvärmekontroll"**.

För detaljer om konfigurationsalternativen, se [hjälpfilen](HELP_sv.md).

## Användning

När komponenten är konfigurerad kommer en ny `climate`-entitet att finnas tillgänglig i Home Assistant. Denna kan läggas till i Lovelace UI och användas i automationer.

## Bidra

Bidrag i form av felrapporter (issues) eller pull requests är välkomna på [GitHub-repot](https://github.com/AlleHj/home-assistant-varmegolv_kontroll).

## Ändringslogg

### Version 2.3.4 (2025-05-28)
* **FIX:** Återinförde import av `Any` från `typing` i `climate.py` för att korrigera "Undefined name `Any`" för typ-hinten i `async_set_temperature` och andra metoder som kan använda `**kwargs`. Lade även till typ-hint för returvärdet på `device_info`.

### Version 2.3.3 (2025-05-28)
* **FIX:** Åtgärdat ett flertal varningar från Ruff och Pylint i alla `.py`-filer. Detta inkluderar:
    * Korrekt formatering av modul-docstrings (D205, D212, D400, D415).
    * Tillägg av saknade docstrings för publika klasser, metoder och funktioner (D101, D102, D103, D107).
    * Borttagning av oanvända importer (`functools`, `UnitOfTemperature`) (F401, W0611).
    * Uppdatering av importer enligt moderna standarder (`collections.abc` för `Callable`, `list` istället för `typing.List`) (UP035).
    * Sortering av import-block (I001).
    * Ändring av f-string-formatering i loggutskrifter till %-formatering (G004, W1203).
    * Uppdatering av typ-annoteringar till PEP 604 (`X | Y`) och PEP 585 (`list`) (UP006, UP007).

### Version 2.3.2 (2025-05-28)
* **FÖRBÄTTRING:** Justerat loggningsnivåer i `climate.py`. Flera tidigare `INFO`-loggar är nu `DEBUG`-loggar och styrs av debug-checkboxen. Kritiska meddelanden om konfigurationsändringar, användarinitierade tillståndsändringar och de specifika meddelandena när värmaren aktivt slås på/av eller styrs är kvar som `INFO`. Detta minskar mängden `INFO`-loggar vid normal drift utan debug aktiverat.

### Version 2.3.1 (2025-05-28)
* **FIX:** Korrigerad hantering av `EVENT_HOMEASSISTANT_START`-lyssnaren i `climate.py` för att förhindra `ValueError` vid avregistrering efter att lyssnaren redan har aktiverats. Detta löser ett problem där avregistreringsanropet misslyckades om det skedde efter att Home Assistant startat och lyssnaren redan hade kört och avregistrerats automatiskt.
* **FÖRBÄTTRING:** `HELP_URL` i `config_flow.py` uppdaterad för att peka på `HELP_sv.md` i roten av GitHub-repot. Länken i `README.md` till `HELP_sv.md` är också uppdaterad.

### Version 2.3.0 (2025-05-28)
* **NYTT:** Lade till alternativ för att aktivera/deaktivera detaljerad debug-loggning per termostatinstans. Detta styrs via en checkbox i "Alternativ" för varje konfigurerad termostat.
* **NYTT:** Skapade en detaljerad `HELP_sv.md`-fil som beskriver installation, konfiguration och användning.
* **FÖRBÄTTRING:** Lade till länkar till hjälpfilen direkt i konfigurations- och options-flödena i användargränssnittet.
* **FÖRBÄTTRING:** `manifest.json` uppdaterad med korrekt `codeowners` och länkar till GitHub-repo. Versionsnummer uppdaterat. Fältet `version_history` borttaget då historiken nu finns i README.
* **FÖRBÄTTRING:** `config_flow.py` hanterar nu den nya debug-optionen och inkluderar den vid skapande av entry samt i options-flödet.
* **FÖRBÄTTRING:** `climate.py`:
    * Implementerade logik för att endast skriva ut `_LOGGER.debug`-meddelanden om den nya debug-optionen är aktiv för instansen.
    * Säkerställde att debug-inställningen läses och uppdateras korrekt när options ändras.
    * Förtydligade hanteringen av `_config_data` och initiala värden vid återställning.
    * Justerad `_set_heater_state` för att undvika onödiga serviceanrop om switchen redan är i önskat läge.
* **FÖRBÄTTRING:** `__init__.py`:
    * Tog bort den globala options-lyssnaren då entiteten nu hanterar detta mer direkt.
    * Utökade `async_migrate_entry` för att säkerställa att befintliga version 2-entries får den nya debug-optionen med defaultvärde.
* **FÖRBÄTTRING:** Svenska översättningsfilen (`sv.json`) uppdaterad med texter för den nya debug-optionen och hjälplänkar. Filen `en.json` borttagen för att endast stödja svenska.
* **FÖRBÄTTRING:** Detaljerad versionshistorik borttagen från enskilda `.py`-filers huvuden, ersatt med en enkel datum- och versionsstämpel. All historik centraliserad till denna README.

### Version 2.2.2 (2025-05-24)
* **FIX:** Korrigerat `TypeError` i `_perform_initial_updates_and_control` (`climate.py`) genom att ta bort felaktigt `await` på synkron funktion.

### Version 2.2.1 (2025-05-23)
* **FÖRBÄTTRING:** Explicit `_attr_name = None` i `climate.py` för tydlighet i namngivning (relevant när `_attr_has_entity_name = True`).

### Version 2.2.0 (2025-05-23)
* **FÖRBÄTTRING:** Omarbetat anrop till switch-tjänster i `climate.py`: Använder nu `self.hass.async_add_executor_job(functools.partial(self.hass.services.call, ..., blocking=True, ...))` för att undvika blockering av Home Assistants händelseloop, särskilt viktigt för KNX-enheter. Kontrollerar även switchens nuvarande tillstånd för att undvika onödiga anrop.

### Version 2.1.6 (2025-05-23)
* **TEST:** Förnyat försök med `switch.call` och `blocking=True` (del av felsökningsprocessen).

### Version 2.1.5 (2025-05-23)
* **TEST:** Switch-anrop tillfälligt bortkommenterat för felsökning.

### Version 2.1.4 (2025-05-23)
* **TEST:** Testat `switch.call` med `blocking=True`.

### Version 2.1.3 (2025-05-23)
* **FÖRBÄTTRING:** Utökad loggning för felsökning av krascher.

### Version 2.1.2 (2025-05-23)
* **FÖRBÄTTRING:** Förhindrar onödig global omladdning av config entry när options (t.ex. HVAC-läge) ändras i `__init__.py`, då climate-entiteten hanterar detta live. Detta bör minska "ValueError" för lyssnare.

### Version 2.1.1 (2025-05-23)
* **FÖRBÄTTRING:** Förbättrad loggning och tillståndshantering.

### Version 2.1.0 (2025-05-23)
* **NYTT:** Stöd för flera instanser med unika namn. Namnfältet är nu obligatoriskt i konfigurationen (`config_flow.py`).
* **NYTT:** `CONF_NAME` tillagd i `const.py`.
* **FÖRBÄTTRING:** Titeln på config entry sätts nu till det angivna namnet.

### Version 2.0.0 (2025-05-23)
* **STOR ÄNDRING:** Komponenten agerar nu som en egen termostat (`climate`-entitet). `CONF_THERMOSTAT_ENTITY` borttagen.
* **NYTT:** `DEFAULT_TARGET_TEMP` tillagd i `const.py`.

### Version 1.0.1 (2025-05-23)
* **NYTT:** `DEFAULT_HYSTERESIS` och `STATE_MASTER_ENABLED` tillagda i `const.py`.

### Version 1.0.0 (2025-05-23)
* Initialversion. Definierar `DOMAIN` och initiala konfigurationsnycklar i `const.py`.

## Licens
Detta projekt är licensierat under Apache License 2.0. Se `LICENSE`-filen (om sådan finns) för detaljer.
*(Antagande om licens, lägg till en LICENSE-fil om det behövs)*