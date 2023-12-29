#  Historical sensors for Home Assistant ![](icon-64.png)

<!-- Code and releases -->

![GitHub Release (latest SemVer including pre-releases)](https://img.shields.io/github/v/release/ldotlopez/ha-historical-sensor?include_prereleases)
[![CodeQL](https://github.com/ldotlopez/ha-historical-sensor/actions/workflows/codeql-analysis.yml/badge.svg)](https://github.com/ldotlopez/ha-historical-sensor/actions/workflows/codeql-analysis.yml)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)

<!-- Sponsors -->
<a href="https://www.buymeacoffee.com/zepolson" target="_blank">
    <img
       src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png"
       alt="Buy Me A Coffee" style="height: 30px !important;width: 105px !important;" >
</a>

Feed historical data into Home Assistant database.

HomeAssistant architecture is built around polling (or pushing) data
from devices, or data providers, in "real-time". Some data sources
(e.g, energy, water or gas providers) can't be polled in real-time or
readings are not accurate. However reading historical data, like last
month consumption, it is possible and accurate. This module adds support
to this.

This module uses the `recorder` component and custom state creation to
store states "from the past".

Current projects using this module:

- [ideenergy energy monitor](https://github.com/ldotlopez/ha-ideenergy)
- [AuroraPlusHA](https://github.com/LeighCurran/AuroraPlusHA)

## How to implement a historical sensor

💡 Check the delorian test integration in this repository

1. Import home_assistant_historical_sensor and define your sensor.
   _⚠️ **Don't** set the SensorEntity.state property. See FAQ below_

```
from homeassistant_historical_sensor import (
    HistoricalSensor, HistoricalState, PollUpdateMixin,
)


class Sensor(PollUpdateMixin, HistoricalSensor, SensorEntity):
    ...
```


2. Define the `SensorEntity.async_update_historical` method and save your
historical states into the `HistoricalSensor._attr_historical_states`
attribute.

```
   async def async_update_historical(self):
        self._attr_historical_states = [
            HistoricalState(state=x.state, dt=x.when) for x in api.fetch()
        ]
```

3. Done Besides other Home Assistant considerations, this is everything
you need to implement data importing into Home Assistant

## How to add statistics to your Historical Sensor

Generating statistics it is not an easy generalizable job,
HistoricalSensor provides some support and helpers but you have to write
some code.

1. Define the `statistic_id` property for your sensor. For simplicity, you
can use the entity_id.  _⚠️ **Don't** set the SensorEntity.state_class
property. See FAQ below_

```
@property def statistic_id(self) -> str:
    return self.entity_id
```


2. Define the `get_statistic_metadata` method for your sensor.

It's recommended to use just "sum" or "mean" statistics, not both,
the one which applies to your sensor. Both are shown here just as example.

```
def get_statistic_metadata(self) -> StatisticMetaData:
    meta = super().get_statistic_metadata() meta["has_sum"] = True
    meta["has_mean"] = True

    return meta
```

3. Define the `async_calculate_statistic_data` method for your sensor.

(Check the delorian integration for a full example)

``` async def async_calculate_statistic_data(
    self, hist_states: list[HistoricalState], *, latest: StatisticsRow |
    None = None,
) -> list[StatisticData]:
   ...
```

## Technical details

Q. **How it is accomplished?.**

A. It's a relatively easy answer but needs to be broken into some pieces:

  1. A new property for sensors: `_attr_historical_states`. This property
  holds a list of `HistoricalState`s which are, basically, a `state`
  value and a `dt` `datetime`  (with tzinfo), so… the data we want.

  2. A new hook for sensor: `async_update_historical`. This method is
  responsible to update `_attr_historical_states` property.
     **This is the only function that needs to be implemented**.

  3. A new method, implemented by `HistoricalSensor` class:
  `async_write_ha_historical_states`. This method handles the details of
  creating tweaked states in the past and write them into the database
  using the `recorder` component of Home Assistant core.

Q. **What is `PollUpdateMixin` and why I need to inherit from it?**

A. Home Assistant sensors can use [the poll or the push model](https://developers.home-assistant.io/docs/integration_fetching_data/#push-vs-poll) to update data.

Poll mode does not mix well with historical data, causes blanks and empty points in history and graphs. Because of that, historical sensors use a false push model: historical sensors are never updated by them self.

`PollUpdateMixin` solves this and automatically provides the poll functionality back without any code. The sensor will be updated at startup and every hour. This interval can be configured via the `UPDATE_INTERVAL` class attribute.

Q. **Why it is recommended to DON'T set the `state` and the `state_class`
properties?**

A. Because it messes up graphs and statistics

* By setting the `state` attr you are telling Home Assistant that
you have a current state, which is not true if you are importing data
from the past. You may think that the last state (now - X hours) may
be the current `state` but it is not, in X hours you will import new
data and that point may have a different value. Also messes graphs with
inconsistent data points.  * Setting `state_class` causes Home Assistant
to calculate statistics data which is not what you want since you are
working with historical data and not present data. Statistical data
will be incorrect if any is calculated. Historical sensors have helper
functions to deal with statistics

**Q. Why my sensor is not shown in the energy panel configuration?**

A. Energy dashboard doesn't use sensors, it uses statistics (it is a
bit confusing, yes). Statistics usually have the same name (id) as the
source sensor, hence the confusion.

If your sensor doesn't show up in energy panel options it is because it
is not generating statistics. For a standard sensor Home Assistant does
that job but HistoricalSensor it is not.

HistoricalSensor basically inserts states into the database, using
almost raw SQL INSERT stamens, so any internal process of HomeAssistant
doesn't apply.

See "How to implement statistics about".

Statistics will be calculated once new historical data comes in, then
it will show up in the energy panel.

**Q. I can't calculate energy, water o gas costs**

A. Actually it can't be done.

Maybe the energy [websocket
API](https://github.com/home-assistant/core/blob/master/homeassistant/components/energy/websocket_api.py)
can be useful


**Q. Why is my historical sensor in an "undefined" state?.**

A. Historical sensors don't provide the current state. Keep in mind
that the last state (from some hours ago) is NOT the current state. The
current state is unknown.

**Q. I want to provide current state AND historical data**

A. You need to implement two sensors: one for the current state and
another one for historical data.

If you are following the [data
coordinator](https://developers.home-assistant.io/docs/integration_fetching_data/#coordinated-single-api-poll-for-data-for-all-entities)
pattern it should be straightforward

### External vs. internal statistics

Due to the way the data is inserted a posteriori into the recorder, Home
Assistant cannot calculate statistics on historical states automatically.
This is particularly problematic for the Energy dashboard, which relies
on these statistics.

It is possible to provide those statistics by

  1. Providing a `get_statistic_metadata` method returning a dictionary of
     supported statistics. Generally, the sum is sufficient for the
     energy dashboard, so setting `has_sum` to True is all it takes

  2. Providing an `async_calculate_statistic_data` method to do the
  calculation.

     It will take a list of `HistoricalState`, and the latest
     `homeassistant.components.recorder.statistics.StatisticsRow`
     as arguments, and should return an array of
     `homeassistant.components.recorder.models.StatisticData` (with
     `start`, `state` and the statistics, e.g., `sum`).

### Importing CSV files

To be implemented: [https://github.com/ldotlopez/ha-historical-sensor/issues/3](https://github.com/ldotlopez/ha-historical-sensor/issues/3)

## Licenses

  - Logo by Danny Allen (Public domain license)
    [https://publicdomainvectors.org/es/vectoriales-gratuitas/Icono-de-configuraci%C3%B3n-del-reloj/88901.html](https://publicdomainvectors.org/es/vectoriales-gratuitas/Icono-de-configuraci%C3%B3n-del-reloj/88901.html)
