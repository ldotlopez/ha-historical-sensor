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

Feed historical statistics into Home Assistant database.

HomeAssistant architecture is built around polling (or pushing) data
from devices, or data providers, in "real-time". Some data sources
(e.g, energy, water or gas providers) can't be polled in real-time or
readings are not accurate. However reading historical data, like last
month consumption, is possible and accurate. This module adds support
to this.

This module uses the `recorder` component and Home Assistant's official
statistics API to import historical statistics data.

Current projects using this module:

- [ideenergy energy monitor](https://github.com/ldotlopez/ha-ideenergy)
- [AuroraPlusHA](https://github.com/LeighCurran/AuroraPlusHA)

## Important: v3.0 Breaking Changes

**Version 3.0 removes state writing entirely.** Historical sensors now only write statistics, not individual states. This means:

✅ **What still works:**
- Energy dashboard integration
- Long-term statistics and trends
- Hourly/daily/monthly aggregated data
- All existing integration code (minimal changes needed)

❌ **What no longer works:**
- Individual state points in entity history graphs
- Granular state visualization in the UI

**Why this change?** Directly manipulating Home Assistant's recorder database was extremely complex, fragile, and error-prone. The code for maintaining state chains, handling schema changes, and managing database integrity was unsustainable. Statistics provide everything needed for 99% of use cases while using Home Assistant's official, stable API.

See [https://github.com/ldotlopez/ha-historical-sensor/issues/18] for detailed explanation and migration guide.

## What Makes `HistoricalSensor` Special

`HistoricalSensor` is not a normal Home Assistant sensor. It exists to import past measurements into Home Assistant statistics, not to expose a live state.

The important differences are:

- The entity state stays `Unknown`; the current reading is intentionally not represented as a live state.
- You fill `self._attr_historical_states` in `async_update_historical()` with `HistoricalState` objects.
- `get_statistic_metadata()` must return valid statistics metadata, including `unit_class`, `unit_of_measurement`, and the flags that describe how the statistic should be aggregated.
- `async_calculate_statistic_data()` is where you turn historical points into `StatisticData` rows.
- The library handles overlap detection and writes statistics through Home Assistant's official external statistics API.

The delorian integration in [`custom_components/delorian/sensor.py`](custom_components/delorian/sensor.py) is the best reference for the actual entity shape and data flow.

## How to implement a historical sensor

If you only need the entity-level pattern, the steps below are the core sensor implementation details. The delorian integration above combines them with the Home Assistant custom-component scaffolding.

1. Import home_assistant_historical_sensor and define your sensor.
   _⚠️ **Don't** set the SensorEntity.state_class property. See FAQ below_
```python
from homeassistant_historical_sensor import (
    HistoricalSensor,
    HistoricalState,
)


class Sensor(HistoricalSensor, SensorEntity):
    ...
```

2. Define the `async_update_historical` method and save your
historical states into the `HistoricalSensor._attr_historical_states`
attribute.
```python
async def async_update_historical(self):
    self._attr_historical_states = [
        HistoricalState(state=x.state, timestamp=x.when.timestamp())
        for x in await api.fetch()
    ]
```

Note: `timestamp` expects a Unix timestamp (float).

3. Define the `get_statistic_metadata` method for your sensor.
```python
def get_statistic_metadata(self) -> StatisticMetaData:
    meta = super().get_statistic_metadata()
    meta["has_sum"] = True  # For counters (energy, water, gas)
    meta["source"] = self.entity_id.split(".", 1)[0]
    meta["unit_class"] = EnergyConverter.UNIT_CLASS
    meta["unit_of_measurement"] = UnitOfEnergy.KILO_WATT_HOUR

    return meta
```

4. Define the `async_calculate_statistic_data` method for your sensor.

This method calculates statistics from your historical states. Check the delorian integration for a full example.
```python
async def async_calculate_statistic_data(
    self,
    hist_states: list[HistoricalState],
    *,
    latest: StatisticsRow | None = None,
) -> list[StatisticData]:
    # Calculate hourly statistics from your states
    # Return list of StatisticData with start, state, sum/mean
    ...
```

5. Done! Besides other Home Assistant considerations, this is everything
you need to implement statistics importing into Home Assistant.

## Technical details

**Q. How does it work?**

A. The architecture is straightforward:

  1. **`_attr_historical_states` property**: Holds a list of `HistoricalState` objects, each containing a `state` value and a `timestamp` (Unix timestamp as float).

  2. **`async_update_historical` hook**: Your implementation updates `_attr_historical_states` with data from your source. **This is the only method you must implement.**

  3. **`async_calculate_statistic_data` method**: Calculates statistics (sum/mean/min/max) from historical states. **You must implement this to generate statistics.**

    4. **`async_write_historical` method**: Implemented by `HistoricalSensor`, handles writing statistics to Home Assistant using the official `async_add_external_statistics` API.

**Q. What happened to state writing?**

A. **Removed in v3.0.** Writing states directly to the database was extremely complex and fragile. The module now only writes statistics using Home Assistant's official API, which is:
- Simpler and more maintainable
- Forward-compatible with HA updates
- Sufficient for energy dashboards and long-term trends

Individual state points no longer appear in entity history graphs, but statistics work perfectly for energy monitoring and trend analysis.

**Q. Why should I NOT set the `state_class` property?**

A. Because it causes Home Assistant to calculate its own statistics from the sensor's current state, which:
- Doesn't make sense for historical data
- Creates incorrect/duplicate statistics
- Conflicts with your manual statistics calculations

Historical sensors provide statistics through `async_calculate_statistic_data`, not through `state_class`.

**Q. Why is my sensor in "Unknown" state?**

A. This is expected and correct. Historical sensors don't provide current state—they only import past statistics. The sensor will always show "Unknown" as its state because:
- The last historical data point (from hours/days ago) is NOT the current state
- The current state is genuinely unknown
- Only statistics are meaningful for this type of sensor

**Q. Why doesn't my sensor show up in the energy panel?**

A. Energy dashboard uses statistics, not sensor states. If your sensor doesn't appear:

1. Make sure you've implemented `get_statistic_metadata()` with `has_sum=True`
2. Make sure you've implemented `async_calculate_statistic_data()`
3. Trigger an update to import data and generate statistics
4. Statistics will appear after the first successful import

**Q. What should I return from `get_statistic_metadata()`?**

A. Return metadata that describes the imported statistic, not the live entity state. The important fields are:

- `unit_class`: required. Use the matching Home Assistant unit class for the measurement domain, such as `energy`.
- `unit_of_measurement`: required. Use the exact unit that matches the data being imported, such as `kWh` for energy.
- `source`: usually the integration domain, which the base implementation derives from `entity_id`.
- `statistic_id`: the external statistic id in `<domain>:<object_id>` format. For `sensor.delorian`, this becomes `sensor:delorian`.
- `has_sum`: set this to `True` for cumulative counters such as energy, water, or gas.
- `has_mean`: set this to `True` when average values are meaningful for the statistic.

The default implementation from `HistoricalSensor` already derives `statistic_id` and `source` from `entity_id`. Override only the fields that describe the measurement itself. For energy sensors, import the unit-class helper explicitly:

```python
from homeassistant.util.unit_conversion import EnergyConverter
```

**Q. Can I provide BOTH current state AND historical statistics?**

A. Yes. The sensor can expose real live data, and this library can still generate the appropriate historical statistics. The important constraint is that the sensor should not opt into Home Assistant's native statistics pipeline with `state_class` or related statistics hooks, because that can conflict with the statistics generated by this library.

Use the sensor state for the live value, and let `HistoricalSensor` handle historical imports and recorder statistics through `get_statistic_metadata()` and `async_calculate_statistic_data()`.

If you're using the [data coordinator pattern](https://developers.home-assistant.io/docs/integration_fetching_data/#coordinated-single-api-poll-for-data-for-all-entities), this should be straightforward.

**Q. Can I calculate energy/water/gas costs?**

A. Cost calculation must be done in Home Assistant's Energy dashboard configuration, not in the sensor itself. The Energy dashboard has built-in cost calculation features.

The energy [websocket API](https://github.com/home-assistant/core/blob/master/homeassistant/components/energy/websocket_api.py) may be useful for advanced use cases.

**Q. Do I need to worry about overlapping data when re-importing?**

A. No. The library handles this automatically:
- New statistics are only added if they're newer than the last imported statistic
- You can safely re-run imports without creating duplicates

## Migration from v2.x to v3.x

### Breaking Changes

1. **`HistoricalState` parameter renamed**: `ts` → `timestamp` (but `ts` still works for backward compatibility)

2. **`group_by_interval` parameter fixed**: `granurality` → `granularity` (typo fix)

3. **Minimum Home Assistant version**: Now requires HA >= 2025.12.0

4. **`statistic_id` property removed**: Statistics now derive an external statistic id from `entity_id`

5. **No more state writing**: Only statistics are written to the database

### What You Need to Update
```python
# Before (v2.x)
HistoricalState(state=value, ts=timestamp)

# After (v3.x) - both work, but timestamp is preferred
HistoricalState(state=value, timestamp=timestamp)
HistoricalState(state=value, ts=timestamp)  # Still supported

# Before (v2.x)
group_by_interval(states, granurality=3600)

# After (v3.x)
group_by_interval(states, granularity=3600)
```

### What Stays the Same

✅ The integration API is unchanged  
✅ `async_update_historical()` works the same  
✅ `async_calculate_statistic_data()` works the same  
✅ `get_statistic_metadata()` works the same  
✅ Energy dashboard integration works the same  

### What's Removed (probably not relevant to you)

- All internal state writing methods
- Direct database manipulation utilities
- `statistic_id` property (external statistic id derived from `entity_id`)
- `patches.py` module

## Helper Functions

### `group_by_interval`

Groups historical states into time intervals (typically hourly) for statistics calculation:
```python
from homeassistant_historical_sensor import group_by_interval

for block_timestamp, states_in_hour in group_by_interval(
    hist_states,
    granularity=60 * 60  # 1 hour in seconds
):
    states = list(states_in_hour)
    # Calculate statistics for this hour
    ...
```

## Importing CSV files

To be implemented: [https://github.com/ldotlopez/ha-historical-sensor/issues/3](https://github.com/ldotlopez/ha-historical-sensor/issues/3)

## Licenses

  - Logo by Danny Allen (Public domain license)
    [https://publicdomainvectors.org/es/vectoriales-gratuitas/Icono-de-configuraci%C3%B3n-del-reloj/88901.html](https://publicdomainvectors.org/es/vectoriales-gratuitas/Icono-de-configuraci%C3%B3n-del-reloj/88901.html)
