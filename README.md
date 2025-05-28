# Home Assistant Anpassad Golvvärmekontroll (varmegolv_kontroll)

Detta är en anpassad komponent (custom component) för Home Assistant som tillhandahåller en termostatfunktion för att styra elektrisk golvvärme eller liknande värmesystem. Den använder en angiven temperatursensor och en switch-entitet för att reglera värmen.

**Aktuell version:** `2.3.1` (2025-05-28)

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

(... resten av ändringsloggen från tidigare ...)

## Licens
Detta projekt är licensierat under Apache License 2.0. Se `LICENSE`-filen (om sådan finns) för detaljer.
*(Antagande om licens, lägg till en LICENSE-fil om det behövs)*