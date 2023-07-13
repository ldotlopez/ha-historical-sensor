#  Historical sensors for Home Assistant ![](icon-64.png)

<!-- Code and releases -->
![GitHub Release (latest SemVer including pre-releases)](https://img.shields.io/github/v/release/ldotlopez/ha-historical-sensor?include_prereleases)
[![CodeQL](https://github.com/ldotlopez/ha-historical-sensor/actions/workflows/codeql-analysis.yml/badge.svg)](https://github.com/ldotlopez/ha-historical-sensor/actions/workflows/codeql-analysis.yml)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)

<!-- Sponsors -->
<a href="https://www.buymeacoffee.com/zepolson" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" style="height: 30px !important;width: 105px !important;" ></a>

Feed historical data into Home Assistant database.

HomeAssistant architecture is built around polling (or pushing) data from devices, or data providers, in "real-time". Some data sources (e.g, energy, water or gas providers) can't be polled in real-time or readings are not accurate. However reading historical data, like last month consumption, it's possible and accurate. This module adds support to this.

This module uses the `recoder` component and custom state creation to store states "from the past".

Current projects using this module:

- [ideenergy energy monitor](https://github.com/ldotlopez/ha-ideenergy)


## Technical details

Q. How it's accomplished?.

A. It's a relatively easy answer but needs to be broken into some pieces:

  1. A new property for sensors: `historical_states`. This property holds a list of `HistoricalState`s which are, basically, a `state`+`datetime`  (with tzinfo), so… the data we want.

  2. A new hook for sensor: `async_update_historical_states`. This method is responsible to update `historical_states` property.  
     **This is the only function that needs to be implemented**.

  3. A new method, implemented by HistoricalSensor class: `async_write_ha_historical_states`. This method handles the details of creating tweaked states in the past and write them into the database using the `recorder` component of Home Assistant core.

Q. Something else?

A. Historical sensors can't provide the current state, Home Assistant will show "undefined" state forever, it's OK and intentional.


### External vs. internal statistics

### Importing CSV files


## Licenses

  - Logo by Danny Allen (Public domain license)
    [https://publicdomainvectors.org/es/vectoriales-gratuitas/Icono-de-configuraci%C3%B3n-del-reloj/88901.html](https://publicdomainvectors.org/es/vectoriales-gratuitas/Icono-de-configuraci%C3%B3n-del-reloj/88901.html)
