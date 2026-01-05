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


import logging
from abc import abstractmethod
from datetime import datetime, timedelta
from functools import cached_property
from typing import Any

from homeassistant.components.recorder.models import StatisticData, StatisticMetaData
from homeassistant.components.recorder.statistics import (
    StatisticMeanType,
    StatisticsRow,
    async_import_statistics,
)
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import STATE_UNKNOWN
from homeassistant.helpers.event import async_track_time_interval

from . import timemachine as tm

LOGGER = logging.getLogger(__name__)


# You must know:
# * DB keeps datetime object as utc
# * Each time hass is started a new record is created, that record can be 'unknow'
#   or 'unavailable'


class HistoricalSensor(SensorEntity):
    """The HistoricalSensor class provides:

    - self.historical_states
    - self.should_poll
    - self.state
    - self.async_added_to_hass()

    Sensors based on HistoricalSensor must provide:
    - self._attr_historical_states
    - self.async_update_historical()
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._attr_historical_states: list[tm.HistoricalState] = []

    @cached_property
    def should_poll(self) -> bool:
        # HistoricalSensors MUST NOT poll.
        # Polling creates incorrect states at intermediate time points.

        return False

    @property
    def state(self) -> Any:
        # Better report unknown than anything
        #
        # Another aproach is to return data from historical entity, but causes
        # wrong results. Keep here for reference.
        #
        # HistoricalSensors doesn't use poll but state is accessed only once when
        # the sensor is registered for the first time in the database
        #
        # if state := self.historical_state():
        #     return float(state)

        return STATE_UNKNOWN

    @property
    def historical_states(self) -> list[tm.HistoricalState]:
        if hasattr(self, "_attr_historical_states"):
            return self._attr_historical_states

        raise NotImplementedError()

    @abstractmethod
    async def async_update_historical(self):
        """async_update_historical()

        This method should be be implemented by sensors

        Implement this async method to fetch historical data from provider and store
        into self._attr_historical_states
        """
        raise NotImplementedError()

    async def async_added_to_hass(self):
        await super().async_added_to_hass()

        #
        # Setting state_class enables HomeAssistant to run statistic calculations on
        # this sensor.
        # We handle our own statistics and can be different from the Home Assisstant
        # ones (also, we don't fully understand some internal procedures of
        # HomeAssistant)
        #

        if getattr(self, "state_class", None):
            LOGGER.warning(
                f"{self.entity_id}: state_class attribute is set. "
                + "This is NOT supported, your statistics will be messed sooner or later"
            )

    async def async_write_historical(self):
        """async_write_historical()

        This method writes `self.historical_states` into database
        """

        if not self.historical_states:
            LOGGER.warning(f"{self.entity_id}: no historical states available")
            return

        LOGGER.debug(
            f"{self.entity_id}: {len(self.historical_states)} historical states present"
        )

        # Write statistics
        await self._async_write_statistics(self.historical_states)

    async def _async_write_statistics(
        self, hist_states: list[tm.HistoricalState]
    ) -> list[StatisticData]:
        if not hist_states:
            return []

        hist_states = list(sorted(hist_states, key=lambda x: x.timestamp))

        statistics_metadata = self.get_statistic_metadata()
        latest_statistic_data = await tm.hass_get_last_statistic(
            self.hass, statistics_metadata
        )

        #
        # Handle overlaping stats.
        #

        if latest_statistic_data is not None:
            cutoff = latest_statistic_data["start"] + 60 * 60
            hist_states = [x for x in hist_states if x.timestamp > cutoff]

        #
        # Calculate stats
        #
        statistics_data = await self.async_calculate_statistic_data(
            hist_states, latest=latest_statistic_data
        )
        async_import_statistics(self.hass, statistics_metadata, statistics_data)

        n_statistics_data = len(statistics_data)
        LOGGER.info(f"{self.entity_id}: added {n_statistics_data} statistics points")
        LOGGER.info(f"{self.entity_id}:      start={latest_statistic_data}")
        LOGGER.info(f"{self.entity_id}:      meta={statistics_metadata}")

        return statistics_data

    def get_statistic_metadata(self) -> StatisticMetaData:
        metadata = StatisticMetaData(
            # has_mean=False,
            has_sum=False,
            mean_type=StatisticMeanType.NONE,
            name=f"{self.name} Statistics",
            source="recorder",
            statistic_id=self.entity_id,
            unit_class=None,
            unit_of_measurement=self.unit_of_measurement,
        )

        return metadata

    async def async_calculate_statistic_data(
        self,
        hist_states: list[tm.HistoricalState],
        *,
        latest: StatisticsRow | None = None,
    ) -> list[StatisticData]:
        raise NotImplementedError()


class PollUpdateMixin(HistoricalSensor):
    """PollUpdateMixin for simulate poll update model

    This mixin provides:

      - UPDATE_INTERVAL: timedelta
      - async_added_to_hass(self)
      - async_will_remove_from_hass(self)
      - _async_historical_handle_update(self)
    """

    """Historical Sensors have long update periods"""
    UPDATE_INTERVAL: timedelta = timedelta(hours=1)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._remove_time_tracker_fn = None

    async def async_added_to_hass(self) -> None:
        """Once added to hass:
        - Setup internal stuff with the Store to hold internal state
        - Setup a peridioc call to update the entity
        """

        await super().async_added_to_hass()

        LOGGER.debug(f"{self.entity_id}: added to hass, do initial update")
        await self._async_historical_handle_update()
        self._remove_time_tracker_fn = async_track_time_interval(
            self.hass,
            self._async_historical_handle_update,
            self.UPDATE_INTERVAL,
        )

        LOGGER.debug(
            f"{self.entity_id}: "
            + f"updating each {self.UPDATE_INTERVAL.total_seconds()} seconds "
        )

    async def async_will_remove_from_hass(self) -> None:
        if self._remove_time_tracker_fn:
            self._remove_time_tracker_fn()

    async def _async_historical_handle_update(self, _: datetime | None = None) -> None:
        await self.async_update_historical()
        await self.async_write_historical()
