# Hjälp för Golvvärmekontroll Integration (varmegolv_kontroll)

Version: 2.3.0
Datum: 2025-05-28

## Innehållsförteckning
1.  [Översikt](#1-översikt)
2.  [Funktioner](#2-funktioner)
3.  [Installation](#3-installation)
4.  [Konfiguration (via Användargränssnitt)](#4-konfiguration-via-användargränssnitt)
    * [Initial Konfiguration (Lägg till Integration)](#initial-konfiguration-lägg-till-integration)
    * [Alternativ (Efter Installation)](#alternativ-efter-installation)
5.  [Användning](#5-användning)
6.  [Felsökning](#6-felsökning)

## 1. Översikt
Golvvärmekontroll är en anpassad komponent för Home Assistant som låter dig skapa en virtuell termostat för att styra elektrisk golvvärme eller liknande värmesystem. Den använder en extern temperatursensor för att mäta aktuell temperatur och en extern switch-entitet (t.ex. ett relä eller KNX-ställdon) för att slå på/av värmeelementet.

## 2. Funktioner
* **Fristående Termostat:** Varje instans av komponenten skapar en egen `climate`-entitet.
* **Temperaturreglering med Hysteres:** Undviker att värmen slår på/av för ofta.
* **Styrning av Extern Switch:** Kontrollerar en switch-entitet i Home Assistant.
* **HVAC-lägen:** Stöder `HEAT` (värme på) och `OFF` (värme av).
* **Flera Instanser:** Du kan konfigurera flera termostater för olika zoner/rum.
* **Beständiga Inställningar:** Måltemperatur och HVAC-läge (PÅ/AV) sparas och återställs korrekt efter en omstart av Home Assistant.
* **Grafisk Konfiguration:** All installation och konfiguration sker via Home Assistants användargränssnitt.
* **Dynamisk Debug-loggning:** Möjlighet att aktivera detaljerad loggning per termostatinstans för felsökning.

## 3. Installation
1.  Se till att du har [HACS (Home Assistant Community Store)](https://hacs.xyz/) installerat, eller installera manuellt.
2.  **Via HACS (Rekommenderat):**
    * Gå till HACS -> Integrationer.
    * Klicka på de tre prickarna uppe till höger och välj "Anpassade repositories".
    * Lägg till URL:en till detta repository (`https://github.com/AlleHj/home-assistant-varmegolv_kontroll`) och välj kategori "Integration".
    * Hitta "Golvvärmekontroll" i listan och klicka på "Installera".
3.  **Manuell Installation:**
    * Ladda ner den senaste versionen från [GitHub-repot](https://github.com/AlleHj/home-assistant-varmegolv_kontroll).
    * Placera mappen `varmegolv_kontroll` (med alla dess filer) i din Home Assistant-installations `custom_components`-mapp. Om `custom_components`-mappen inte finns, skapa den.
4.  Starta om Home Assistant.

## 4. Konfiguration (via Användargränssnitt)

### Initial Konfiguration (Lägg till Integration)
Efter omstart, gå till:
**Inställningar -> Enheter & Tjänster -> Lägg till Integration -> Sök efter "Golvvärmekontroll"**

Följande fält behöver fyllas i:

* **Termostatens Namn (Unikt):**
    * Ett unikt och beskrivande namn för denna termostatinstans (t.ex. "Golvvärme Badrum"). Detta namn kommer att användas för att identifiera entiteten.
    * *Obligatoriskt.*

* **Nuvarande Temperatursensorentitet:**
    * Entitets-ID för den sensor som rapporterar den aktuella rumstemperaturen (t.ex. `sensor.badrum_temperatur`).
    * *Obligatoriskt.*

* **Värmare På/Av Styrentitet (switch):**
    * Entitets-ID för den switch-entitet som styr själva värmeelementet (t.ex. `switch.badrum_golvvarme_rele`).
    * *Obligatoriskt.*

* **Hysteres (grader):**
    * Temperaturskillnaden som tillåts runt måltemperaturen innan värmen slås på eller av.
    * Exempel: Om måltemp är 20°C och hysteres är 0.5°C:
        * Värmen slås PÅ när temperaturen sjunker till 19.75°C (Mål - Hysteres/2).
        * Värmen slås AV när temperaturen stiger till 20.25°C (Mål + Hysteres/2).
    * Standardvärde: `0.5`

* **Initial Måltemperatur (grader):**
    * Den måltemperatur termostaten ska ha när den först konfigureras eller efter återställning (om inget tidigare värde finns sparat).
    * Standardvärde: `20.0`

* **Aktivera Termostaten Initialt (Huvud På/Av):**
    * Om ibockad, kommer termostatens HVAC-läge att vara `HEAT` (på) när den skapas. Annars `OFF`.
    * Standardvärde: Ibockad (På).

### Alternativ (Efter Installation)
Du kan ändra vissa inställningar för en redan konfigurerad termostatinstans. Gå till:
**Inställningar -> Enheter & Tjänster -> Integrationer -> Hitta "Golvvärmekontroll" och klicka på den instans du vill ändra -> Klicka på "Alternativ" (kugghjulet).**

Följande alternativ kan justeras:

* **Nuvarande Temperatursensorentitet:** (Samma som ovan)
* **Värmare På/Av Styrentitet (switch):** (Samma som ovan)
* **Hysteres (grader):** (Samma som ovan)
* **Aktivera Termostaten (Huvud På/Av):**
    * Styr om termostatens HVAC-läge ska vara `HEAT` (på) eller `OFF`. Detta är samma som att ändra HVAC-läget direkt på termostatkortet.
* **Aktivera Debug-loggning:**
    * Om ibockad kommer detaljerade felsökningsmeddelanden för denna specifika termostatinstans att skrivas till Home Assistant-loggen (under `home-assistant.log`).
    * Detta är användbart för att felsöka problem eller förstå exakt vad komponenten gör.
    * Stäng av när den inte behövs för att undvika överdriven loggning.
    * Standardvärde: Ej ibockad (Av).

## 5. Användning
När integrationen är konfigurerad kommer en ny `climate`-entitet att skapas. Du kan lägga till denna på ditt Lovelace-gränssnitt som ett standard termostatkort. Du kan:
* Se aktuell temperatur.
* Ställa in måltemperatur.
* Slå på (HEAT) eller stänga av (OFF) termostaten.
* Se aktuell åtgärd (värmer, inaktiv, av).

Termostaten kan också styras via automationer och skript med standard `climate`-tjänster (t.ex. `climate.set_temperature`, `climate.set_hvac_mode`).

## 6. Felsökning
* **Problem:** Termostaten slår inte på/av värmen som förväntat.
    * **Kontrollera:**
        * Att rätt temperatursensor och switch-entitet är valda i konfigurationen/alternativen.
        * Att temperatursensorn rapporterar korrekta värden.
        * Att switch-entiteten kan styras manuellt från Home Assistant.
        * Måltemperaturen och hysteresinställningarna.
        * Aktivera "Debug-loggning" under Alternativ för den specifika termostatinstansen och inspektera Home Assistant-loggarna (`Inställningar -> System -> Loggar -> Ladda ner fullständig logg`) för meddelanden märkta med `custom_components.varmegolv_kontroll` och din termostats namn.
* **Problem:** Hittar inte integrationen "Golvvärmekontroll" när jag försöker lägga till den.
    * **Kontrollera:** Att du har startat om Home Assistant efter att ha lagt till komponenten i `custom_components`.
* **Problem:** Felmeddelanden i loggen.
    * Notera felmeddelandet och försök aktivera debug-loggning för mer detaljer. Rapportera gärna problem som "issues" på [komponentens GitHub-sida](https://github.com/AlleHj/home-assistant-varmegolv_kontroll/issues).

---
För ytterligare support, se [GitHub repository](https://github.com/AlleHj/home-assistant-varmegolv_kontroll).