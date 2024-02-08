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

import sqlalchemy.exc
import sqlalchemy.orm
from homeassistant.components import recorder
from homeassistant.components.recorder import db_schema
from homeassistant.components.recorder.models import StatisticData, StatisticMetaData
from homeassistant.components.recorder.statistics import (
    async_add_external_statistics,
    async_import_statistics,
    split_statistic_id,
    valid_statistic_id,
)
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.event import async_call_later, async_track_time_interval

from . import timemachine as tm
from .consts import DELAY_ON_MISSING_STATES_METADATA
from .patches import _build_attributes, _stringify_state
from .state import HistoricalState

_LOGGER = logging.getLogger(__name__)


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
        self._attr_historical_states: list[HistoricalState] = []  # type: ignore[annotation-unchecked]

    async def async_added_to_hass(self):
        await super().async_added_to_hass()

        #
        # Setting state_class enables HomeAssistant to run statistic calculations on
        # this sensor.
        # We handle our own statistics and can be different from the Home Assisstant
        # ones (also, we don't fully understand some internal procedures of
        # HomeAssistant)
        #

        if self.statistic_id and getattr(self, "state_class", None):
            _LOGGER.warning(
                f"{self.entity_id}: state_class attribute is set. "
                + "This is NOT supported, your statistics will be messed sooner or later"
            )

    @cached_property
    def should_poll(self) -> bool:
        # HistoricalSensors MUST NOT poll.
        # Polling creates incorrect states at intermediate time points.

        return False

    @property
    def state(self):
        # Better report unavailable than anything
        #
        # Another aproach is to return data from historical entity, but causes
        # wrong results. Keep here for reference.
        #
        # HistoricalSensors doesn't use poll but state is accessed only once when
        # the sensor is registered for the first time in the database
        #
        # if state := self.historical_state():
        #     return float(state)

        return None

    @property
    def historical_states(self):
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

    async def _schedule_on_missing_states_meta(self, fn) -> bool:
        states_metadata_id = await tm.hass_get_entity_states_metadata_id(
            self.hass, self
        )

        if states_metadata_id is not None:
            return False

        _LOGGER.warning(
            f"{self.entity_id}: not yet fully ready, states meta information is "
            + f"unavailablele, retring in {DELAY_ON_MISSING_STATES_METADATA} seconds."
        )

        async_call_later(self.hass, DELAY_ON_MISSING_STATES_METADATA, fn)
        return True

    async def async_write_ha_historical_states(self, _=None):
        """async_write_ha_historical_states()

        This method writes `self.historical_states` into database
        """

        if await self._schedule_on_missing_states_meta(
            self.async_write_ha_historical_states
        ):
            return

        _LOGGER.debug(f"{self.entity_id} states meta ready")

        # Write states
        n = len(await self._async_write_states(self.historical_states))
        _LOGGER.debug(f"{self.entity_id}: {n} states written into the database")

        # # Write statistics
        n = len(await self._async_write_statistics(self.historical_states))
        _LOGGER.debug(f"{self.entity_id}: {n} statistics points written into database")

    async def _async_write_states(
        self, hist_states: list[HistoricalState]
    ) -> list[db_schema.States]:
        return await recorder.get_instance(self.hass).async_add_executor_job(
            self._recorder_write_states, hist_states
        )

    def _recorder_write_states(
        self, hist_states: list[HistoricalState]
    ) -> list[db_schema.States]:
        if not hist_states:
            return []

        with tm.hass_recorder_session(self.hass) as session:
            #
            # Delete invalid states
            #

            try:
                n_states = len(tm.delete_invalid_states(session, self))
                _LOGGER.debug(f"{self.entity_id}: cleaned {n_states} invalid states")

            except sqlalchemy.exc.IntegrityError:
                session.rollback()
                _LOGGER.debug("Warning: Current recorder schema is not supported")
                _LOGGER.debug(
                    "Invalid states can't be deleted from recorder."
                    + "This is not critical just unsightly for some graphs "
                )

            #
            # Build recorder States
            #

            db_states: list[db_schema.States] = []
            base_attrs_dict = _build_attributes(self)
            for hist_state in hist_states:
                attrs_as_dict = base_attrs_dict | hist_state.attributes
                attrs_as_str = db_schema.JSON_DUMP(attrs_as_dict)

                attrs_as_bytes = (
                    b"{}" if hist_state.state is None else attrs_as_str.encode("utf-8")
                )

                attrs_hash = db_schema.StateAttributes.hash_shared_attrs_bytes(
                    attrs_as_bytes
                )

                state_attributes = db_schema.StateAttributes(
                    hash=attrs_hash, shared_attrs=attrs_as_str
                )

                state = db_schema.States(
                    last_changed_ts=hist_state.ts,
                    last_updated_ts=hist_state.ts,
                    state=_stringify_state(self, hist_state.state),
                    state_attributes=state_attributes,
                )

                db_states.append(state)

            ret = tm.save_states(session, self, db_states, overwrite_overlaping=True)

            return ret

    async def _async_write_statistics(
        self, hist_states: list[HistoricalState]
    ) -> list[HistoricalState]:
        if self.statistic_id is None:
            _LOGGER.debug(f"{self.entity_id}: statistics are not enabled")
            return []

        if not hist_states:
            return []

        statistics_metadata = self.get_statistic_metadata()

        hist_states = list(sorted(hist_states, key=lambda x: x.ts))

        latest_stats_data = await tm.hass_get_last_statistic(
            self.hass, statistics_metadata
        )

        #
        # Handle overlaping stats.
        #

        overwrite = True

        if overwrite:

            def _delete_stats_since(ts: int):
                with tm.hass_recorder_session(self.hass) as session:
                    return tm.delete_statistics_since(
                        session, statistics_metadata["statistic_id"], since=ts
                    )

            deleted_statistics = await recorder.get_instance(
                self.hass
            ).async_add_executor_job(_delete_stats_since, hist_states[0].ts)

            _LOGGER.debug(
                f"{statistics_metadata['statistic_id']}: "
                + f"deleted {len(deleted_statistics)} statistics"
            )

        else:
            if latest_stats_data is not None:
                cutoff = latest_stats_data["start"] + 60 * 60
                hist_states = [x for x in hist_states if x.ts > cutoff]

        #
        # Calculate stats
        #
        statistics_data = await self.async_calculate_statistic_data(
            hist_states, latest=latest_stats_data
        )

        if valid_statistic_id(self.statistic_id):
            async_add_external_statistics(
                self.hass, statistics_metadata, statistics_data
            )
        else:
            async_import_statistics(self.hass, statistics_metadata, statistics_data)

        return hist_states

    @property
    def statistic_id(self) -> str | None:
        return None

    def get_statistic_metadata(self) -> StatisticMetaData:
        if self.statistic_id is None:
            raise ValueError(f"{self.entity_id} statistic_id is None")

        if valid_statistic_id(self.statistic_id):
            source = split_statistic_id(self.statistic_id)[0]
        else:
            source = "recorder"

        metadata = StatisticMetaData(
            has_mean=False,
            has_sum=False,
            name=f"{self.name} Statistics",
            source=source,
            statistic_id=self.statistic_id,
            unit_of_measurement=self.unit_of_measurement,
        )

        return metadata

    async def async_calculate_statistic_data(
        self, hist_states: list[HistoricalState], *, latest: dict | None = None
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

        _LOGGER.debug(f"{self.entity_id}: added to hass, do initial update")
        await self._async_historical_handle_update()
        self._remove_time_tracker_fn = async_track_time_interval(
            self.hass,
            self._async_historical_handle_update,
            self.UPDATE_INTERVAL,
        )

        _LOGGER.debug(
            f"{self.entity_id}: "
            + f"updating each {self.UPDATE_INTERVAL.total_seconds()} seconds "
        )

    async def async_will_remove_from_hass(self) -> None:
        if self._remove_time_tracker_fn:
            self._remove_time_tracker_fn()

    async def _async_historical_handle_update(self, _: datetime | None = None) -> None:
        await self.async_update_historical()
        await self.async_write_ha_historical_states()
