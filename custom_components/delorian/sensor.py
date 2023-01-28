# -*- coding: utf-8 -*-

# Copyright (C) 2021-2022 Luis López <luis@cuarentaydos.com>
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


from datetime import timedelta
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
from homeassistant_historical_sensor import (
    DatedState,
    HistoricalSensor,
    PollUpdateMixin,
)

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
        self._attr_historical_states = [
            DatedState(
                state=state,
                when=dt,
            )
            for dt, state in self.api.fetch()
        ]

    def get_statatistics_metadata(self) -> StatisticMetaData:
        meta = super().get_statatistics_metadata()
        meta["has_sum"] = True
        meta["has_mean"] = True

        return meta

    async def async_calculate_statistic_data(
        self, dated_states: List[DatedState]
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
            #     "end": datetime.datetime(
            #         2023, 1, 28, 0, 0, tzinfo=datetime.timezone.utc
            #     ),
            #     "last_reset": None,
            #     "max": None,
            #     "mean": None,
            #     "min": None,
            #     "start": datetime.datetime(
            #         2023, 1, 27, 23, 0, tzinfo=datetime.timezone.utc
            #     ),
            #     "state": 0.29,
            #     "sum": 1095.3900000000003,
            # }

            accumulated = last_stat["sum"] or 0
            dated_states = [x for x in dated_states if x.when >= last_stat["end"]]

        else:
            accumulated = 0

        def calculate_statistics_from_accumulated(accumulated):
            for x in dated_states:
                accumulated = accumulated + x.state
                yield StatisticData(
                    start=x.when - timedelta(hours=1),
                    state=x.state,
                    mean=x.state,
                    sum=accumulated,
                )

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
