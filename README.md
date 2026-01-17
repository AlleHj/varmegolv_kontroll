![Version](https://img.shields.io/badge/version-2.3.1-blue.svg)
![Home Assistant](https://img.shields.io/badge/home%20assistant-component-orange.svg)


# Golvvärmekontroll

**Golvvärmekontroll** är en anpassad integration (Custom Component) för Home Assistant som låter dig styra elektrisk golvvärme eller andra värmekällor som en virtuell termostat.

Integrationen skapar en `climate`-entitet som reglerar en switch (relä) baserat på värdet från en temperatursensor. Den har inbyggd hysteres för att undvika att reläet slår av/på för ofta.

## Funktioner

*   **Virtuell Termostat:** Fungerar som en fullvärdig termostat i Home Assistant.
*   **Hysteres:** Konfigurerbar hysteres (diff) för stabilare reglering.
*   **Återställning:** Kommer ihåg inställd temperatur och läge (Värme/Av) efter omstart av Home Assistant.
*   **Multipla Instanser:** Skapa flera oberoende termostater för olika rum.
*   **Enkel Konfiguration:** All inställning sker via Home Assistants grafiska gränssnitt (UI).

## Installation

### Alternativ 1: HACS (Rekommenderat)
1. Lägg till denna repository som en anpassad repository i HACS.
2. Sök efter "Golvvärmekontroll" och installera.
3. Starta om Home Assistant.

### Alternativ 2: Manuell Installation
1. Ladda ner källkoden.
2. Kopiera mappen `custom_components/varmegolv_kontroll` till din Home Assistant `config/custom_components/`-mapp.
3. Starta om Home Assistant.

## Konfiguration

1. Gå till **Inställningar** -> **Enheter & Tjänster**.
2. Klicka på **Lägg till integration** nere till höger.
3. Sök efter **Golvvärmekontroll**.
4. Fyll i inställningarna i dialogen:

| Inställning | Beskrivning |
| :--- | :--- |
| **Namn** | Namnet på denna termostat (t.ex. "Badrum", "Hall"). Används för att skapa unikt ID. |
| **Temperatursensor** | Välj entiteten för sensorn som mäter rumstemperaturen (t.ex. `sensor.badrum_temp`). |
| **Värme Switch** | Välj entiteten för switchen/reläet som styr värmen (t.ex. `switch.golvvarme_aktor`). |
| **Måltemperatur** | Standardtemperatur som termostaten startar med vid nyinstallation (t.ex. 22.0). |
| **Hysteres** | Temperaturdiff i grader för att slå av/på. Om satt till 0.5 och måltemp är 22°C:<br>• Värme **PÅ** under 21.5°C (Mål - Hysteres)<br>• Värme **AV** över 22.5°C (Mål + Hysteres) |

## Användning

Efter installation skapas en ny klimatenhet (`climate.golvvarmekontroll_ditt_namn`).

*   **Lägen:**
    *   **Värme (Heat):** Termostaten reglerar värmen automatiskt mot inställd temperatur.
    *   **Av (Off):** Värmen är avstängd helt.
*   **Ändra Inställningar:** Du kan när som helst ändra vilka sensorer som används eller justera hysteresen genom att klicka på **Konfigurera** på integrationens kort under Enheter & Tjänster.

## Exempel på Dashboard-kort

Du kan använda standardkortet "Thermostat" i Lovelace:

```yaml
type: thermostat
entity: climate.golvvarmekontroll_badrum
name: Badrumsgolv
```

## Felsökning

Om du upplever problem kan du aktivera mer detaljerad loggning i `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.varmegolv_kontroll: debug
```
