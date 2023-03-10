# -*- coding: utf-8 -*-

# Copyright (C) 2021-2023 Luis López <luis@cuarentaydos.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301,
# USA.


# TODO
# Maybe we need to mark some function as callback but I'm not sure whose.
# from homeassistant.core import callback


# Check sensor.SensorEntityDescription
# https://github.com/home-assistant/core/blob/dev/homeassistant/components/sensor/__init__.py


import itertools
import statistics
from datetime import datetime, timedelta
from typing import List, Optional

from homeassistant.components.recorder.models import StatisticData, StatisticMetaData
from homeassistant.components.recorder.statistics import get_last_statistics
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ENERGY_KILO_WATT_HOUR
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import DiscoveryInfoType
from homeassistant.util import dt as dtutil
from homeassistant_historical_sensor import HistoricalSensor, PollUpdateMixin
from homeassistant_historical_sensor.sensor import HistoricalState

from .api import API
from .const import DOMAIN, NAME

PLATFORM = "sensor"


class Sensor(PollUpdateMixin, HistoricalSensor, SensorEntity):
    def __init__(self, *args, **kwargs):
        self._attr_has_entity_name = True
        self._attr_name = NAME

        self._attr_unique_id = NAME
        self._attr_entity_id = NAME

        self._attr_entity_registry_enabled_default = True
        self._attr_state = None

        # Simulate energy consumption source
        self._attr_native_unit_of_measurement = ENERGY_KILO_WATT_HOUR
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.MEASUREMENT

        self.api = API()

    async def async_update_historical(self):
        def timestamp_from_local_dt(dt):
            if dt.tzinfo is None:
                dt = dtutil.as_local(dt)

            ts = dtutil.as_timestamp(dt)

            return ts

        self._attr_historical_states = [
            HistoricalState(
                state=state,
                timestamp=timestamp_from_local_dt(dt),
            )
            for (dt, state) in self.api.fetch(
                start=datetime.now() - timedelta(days=3), step=timedelta(minutes=15)
            )
        ]

    def get_statatistics_metadata(self) -> StatisticMetaData:
        meta = super().get_statatistics_metadata()
        meta["has_sum"] = True
        meta["has_mean"] = True

        return meta

    async def async_calculate_statistic_data(
        self, hist_states: List[HistoricalState]
    ) -> List[StatisticData]:
        metadata = self.get_statatistics_metadata()

        res = await self._get_recorder_instance().async_add_executor_job(
            get_last_statistics,
            self.hass,
            1,
            metadata["statistic_id"],
            True,
            set(["last_reset", "max", "mean", "min", "state", "sum"]),
        )

        if res:
            last_stat = res[metadata["statistic_id"]][0]
            # last_stat sample
            # {
            #     "last_reset": None,
            #     "max": None,
            #     "mean": None,
            #     "min": None,
            #     'start': 1678399200.0,
            #     'end': 1678402800.0,
            #     "state": 0.29,
            #     "sum": 1095.3900000000003,
            # }

            accumulated = last_stat["sum"] or 0
            hist_states = [x for x in hist_states if x.timestamp >= last_stat["end"]]

        else:
            accumulated = 0

        def calculate_statistics_from_accumulated(accumulated):
            def hour_for_hist_st(hist_st):
                dt = dtutil.utc_from_timestamp(hist_st.timestamp)
                return dt.replace(minute=0, second=0, microsecond=0)

            for dt, collection in itertools.groupby(hist_states, key=hour_for_hist_st):
                collection = list(collection)
                mean = statistics.mean([x.state for x in collection])
                partial_sum = sum([x.state for x in collection])
                accumulated = accumulated + partial_sum

                basedt = dt - timedelta(hours=1)
                yield StatisticData(
                    start=basedt,
                    state=partial_sum,
                    mean=mean,
                    sum=accumulated,
                )

            # for x in dated_states:
            #     accumulated = accumulated + x.state
            #     yield StatisticData(
            #         start=x.when - timedelta(hours=1),
            #         state=x.state,
            #         mean=x.state,
            #         sum=accumulated,
            #     )

        return list(calculate_statistics_from_accumulated(accumulated))


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_devices: AddEntitiesCallback,
    discovery_info: Optional[DiscoveryInfoType] = None,  # noqa DiscoveryInfoType | None
):
    device_info = hass.data[DOMAIN][config_entry.entry_id]
    sensors = [
        Sensor(config_entry=config_entry, device_info=device_info),
    ]
    async_add_devices(sensors)
