# SMHI Brandrisk for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/wizz666/homeassistant-smhi-brandrisk.svg)](https://github.com/wizz666/homeassistant-smhi-brandrisk/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Fire risk and weather warning sensors for Sweden, powered by [SMHI](https://www.smhi.se) open data APIs.

## Sensors

### Fire Risk (FWI – Fire Weather Index)
Available during fire season (approx. April–October):

| Sensor | Description |
|---|---|
| **Brandrisk (FWI-klass)** | Fire risk class 1–6 with label (Mycket låg → Extrem) |
| **FWI-index** | Raw FWI numerical value |
| **FFMC** | Fine Fuel Moisture Code |
| **DMC** | Duff Moisture Code |
| **DC** | Drought Code |
| **ISI** | Initial Spread Index |
| **BUI** | Build-Up Index |
| **Gräsbrandsrisk** | Grass fire risk class |

Outside fire season, sensors return class 0 with label "Ej brandsäsong".

### Frozen Precipitation Risk (SNOW1g)
Year-round risk of frozen precipitation (ice, sleet):

| Sensor | Description |
|---|---|
| **Fruset nederbördsrisk** | Risk level: Mycket låg → Mycket hög |

### Weather Warnings (IBW)
SMHI's national weather warnings:

| Sensor | Description |
|---|---|
| **Värsta vädervarning** | Highest active warning level (Ingen / Gul / Orange / Röd) |
| **Antal vädervarningar** | Number of active warnings |

## Installation

### Via HACS (recommended)

1. Add this repository as a **Custom Repository** in HACS:
   - HACS → Integrations → ⋮ → Custom repositories
   - URL: `https://github.com/wizz666/homeassistant-smhi-brandrisk`
   - Category: **Integration**
2. Search for **SMHI Brandrisk** and install
3. Restart Home Assistant
4. Go to **Settings → Integrations → + Add Integration → SMHI Brandrisk**

### Manual

1. Copy `custom_components/smhi_brandrisk/` to your HA `custom_components/` directory
2. Restart Home Assistant
3. Go to **Settings → Integrations → + Add Integration → SMHI Brandrisk**

## Configuration

Enter a name and coordinates for your location. The integration validates that coordinates are within Sweden (55–70°N, 10–25°E). Coordinates default to your HA home location.

Multiple locations are supported — add the integration once per location.

## Data Sources

| API | Provider | Update interval |
|---|---|---|
| FWI fire risk forecast | SMHI/MSB | Hourly |
| SNOW1g frozen precipitation | SMHI | Hourly |
| IBW weather warnings | SMHI | Hourly |

All data is from [SMHI Open Data](https://opendata.smhi.se) — free to use under CC BY 4.0.

## Requirements

- Home Assistant 2024.1.0 or newer
- Location within Sweden

## License

MIT License — see [LICENSE](LICENSE)
