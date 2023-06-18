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


import logging
from abc import abstractmethod
from datetime import timedelta
from typing import List, Optional

import sqlalchemy.exc
import sqlalchemy.orm
from homeassistant.components import recorder
from homeassistant.components.recorder import db_schema as db_schema
from homeassistant.components.recorder.models import StatisticData, StatisticMetaData
from homeassistant.components.recorder.statistics import (
    StatisticsRow,
    async_add_external_statistics,
    async_import_statistics,
    split_statistic_id,
    valid_statistic_id,
)
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dtutil

from . import util
from .patches import _stringify_state
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
        self._attr_historical_states: List[HistoricalState] = []  # type: ignore[annotation-unchecked]

    @property
    def should_poll(self):
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

        return []

    @property
    def recorder(self):
        return recorder.get_instance(self.hass)

    @abstractmethod
    async def async_update_historical(self):
        """async_update_historical()

        This method should be be implemented by sensors

        Implement this async method to fetch historical data from provider and store
        into self._attr_historical_states
        """
        raise NotImplementedError()

    async def async_write_ha_historical_states(self):
        """async_write_ha_historical_states()

        This method writes `self.historical_states` into database
        """

        hist_states = self.historical_states
        if any([True for x in hist_states if x.dt.tzinfo is None]):
            _LOGGER.error("historical_states MUST include tzinfo")
            return

        hist_states = list(sorted(hist_states, key=lambda x: x.dt))
        _LOGGER.debug(
            f"{self.entity_id}: "
            f"{len(hist_states)} historical states collected from sensor"
        )

        if not hist_states:
            return

        # Write states
        await self.recorder.async_add_executor_job(
            self._write_recorder_states, hist_states
        )
        await self._write_statistic_data(hist_states)

    def _write_recorder_states(self, hist_states: List[HistoricalState]):
        with recorder.util.session_scope(
            session=self.recorder.get_session()
        ) as session:
            # base_qs = session.query(db_schema.States).filter(
            #     db_schema.States.entity_id == self.entity_id
            # )

            #
            # Delete invalid states
            #

            try:
                # states = base_qs.filter(
                #     or_(
                #         db_schema.States.state == STATE_UNKNOWN,
                #         db_schema.States.state == STATE_UNAVAILABLE,
                #     )
                # )
                # n_states = states.count()
                # states.delete()
                # session.commit()

                n_states = util.delete_invalid_states(session, self.entity_id)
                _LOGGER.debug(
                    f"{self.entity_id}: " f"{n_states} invalid states deleted"
                )

            except sqlalchemy.exc.IntegrityError:
                session.rollback()
                _LOGGER.debug("Warning: Current recorder schema is not supported")
                _LOGGER.debug(
                    "Invalid states can't be deleted from recorder."
                    + "This is not critical just unsightly for some graphs "
                )

            #
            # Check latest state in the database
            #

            try:
                latest = util.get_latest_state(session, self.entity_id)

            except sqlalchemy.exc.DatabaseError:
                _LOGGER.debug(
                    "Error: Current recorder schema is not supported. "
                    + "This error is fatal, please file a bug"
                )
                return

            #
            # Drop historical states older than lastest db state
            #

            # About deleting intersecting states instead of drop incomming
            # overlapping states: This approach has been tested several times and
            # always ends up causing unexpected failures. Sometimes the database
            # schema changes and sometimes, depending on the engine, integrity
            # failures appear. It is better to discard the new overlapping states
            # than to delete them from the database.

            if latest:
                cutoff = dtutil.utc_from_timestamp(latest.last_updated_ts or 0)
                _LOGGER.debug(
                    f"{self.entity_id}: " f"lastest state: {latest.state} @ {cutoff}"
                )
                hist_states = [x for x in hist_states if x.dt > cutoff]

            else:
                _LOGGER.debug(f"{self.entity_id}: no previous states found")

            #
            # Check if there are any states left
            #
            if not hist_states:
                _LOGGER.debug(f"{self.entity_id}: no new states")
                return

            #
            # Build recorder States
            #
            state_meta = util.get_states_meta(session, self.entity_id)

            db_states: List[db_schema.States] = []
            for idx, hist_state in enumerate(hist_states):
                # attrs_as_dict = _build_attributes(self, hist_state.state)
                # attrs_as_dict.update(hist_state.attributes)
                # attrs_as_str = db_schema.JSON_DUMP(attrs_as_dict)

                # attrs_as_bytes = (
                #     b"{}" if hist_state.state is None else attrs_as_str.encode("utf-8")
                # )

                # attrs_hash = db_schema.StateAttributes.hash_shared_attrs_bytes(
                #     attrs_as_bytes
                # )

                # state_attributes = db_schema.StateAttributes(
                #     hash=attrs_hash, shared_attrs=attrs_as_str
                # )

                ts = dtutil.as_timestamp(hist_state.dt)
                state = db_schema.States(
                    # entity_id=self.entity_id,
                    states_meta_rel=state_meta,
                    last_changed_ts=ts,
                    last_updated_ts=ts,
                    old_state=db_states[idx - 1] if idx else latest,
                    state=_stringify_state(self, hist_state.state),
                    # state_attributes=state_attributes,
                )

                # _LOGGER.debug(
                #     f"new state: "
                #     f"dt={dtutil.as_local(hist_state.dt)} value={hist_state.state}"
                # )
                db_states.append(state)

            util.save_states(session, db_states)

            _LOGGER.debug(f"{self.entity_id}: {len(db_states)} saved into the database")

    async def _write_statistic_data(self, hist_states: List[HistoricalState]):
        if self.statatistic_id is None:
            _LOGGER.debug(f"{self.entity_id}: statistics are not enabled")
            return

        statistics_meta = self.get_statatistic_metadata()

        latest = await util.get_last_statistics_wrapper(
            self.hass, statistics_meta["statistic_id"]
        )

        # Don't do this, see notes above "About deleting intersecting states"
        #
        # def delete_statistics():
        #     with recorder.util.session_scope(
        #         session=self.recorder.get_session()
        #     ) as session:
        #         start_cutoff = hist_states[0].when - timedelta(hours=1)
        #         end_cutoff = hist_states[-1].when
        #         qs = (
        #             session.query(db_schema.Statistics)
        #             .join(
        #                 db_schema.StatisticsMeta,
        #                 db_schema.Statistics.metadata_id == db_schema.StatisticsMeta.id,
        #                 isouter=True,
        #             )
        #             .filter(db_schema.Statistics.start >= start_cutoff)
        #             .filter(db_schema.Statistics.start < end_cutoff)
        #         )
        #         stats = [x.id for x in qs]
        #
        #     clear_statistics(self.recorder, stats)
        #     _LOGGER.debug(f"Cleared {len(stats)} statistics")
        #
        # await self.recorder.async_add_executor_job(delete_statistics)

        hist_states = self.historical_states
        if latest is not None:
            cutoff = dtutil.utc_from_timestamp(latest["start"]) + timedelta(hours=1)
            hist_states = [x for x in hist_states if x.dt > cutoff]

        #
        # Calculate stats
        #
        statistics_data = await self.async_calculate_statistic_data(
            hist_states, latest=latest
        )

        for stat in statistics_data:
            tmp = dict(stat)
            start_dt = dtutil.as_local(tmp.pop("start"))
            _LOGGER.debug(f"new statistic: start={start_dt}, value={tmp!r}")

        if valid_statistic_id(self.statatistic_id):
            async_add_external_statistics(self.hass, statistics_meta, statistics_data)
        else:
            async_import_statistics(self.hass, statistics_meta, statistics_data)

        _LOGGER.debug(
            f"{self.entity_id}: collected {len(statistics_data)} statistic points"
        )

    @property
    def statatistic_id(self) -> Optional[str]:
        return None

    def get_statatistic_metadata(self) -> StatisticMetaData:
        if self.statatistic_id is None:
            raise ValueError(f"{self.entity_id} statatistics_id is None")

        if valid_statistic_id(self.statatistic_id):
            source = split_statistic_id(self.statatistic_id)[0]
        else:
            source = "recorder"

        metadata = StatisticMetaData(
            has_mean=False,
            has_sum=False,
            name=f"{self.name} Statistics",
            source=source,
            statistic_id=self.statatistic_id,
            unit_of_measurement=self.unit_of_measurement,
        )

        return metadata

    async def async_calculate_statistic_data(
        self, hist_states: List[HistoricalState], *, latest: Optional[dict]
    ) -> List[StatisticData]:
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
            self._async_historical_handle_update,  # type: ignore[call-arg]
            self.UPDATE_INTERVAL,
        )

        _LOGGER.debug(
            f"{self.entity_id}: "
            + f"updating each {self.UPDATE_INTERVAL.total_seconds()} seconds "
        )

    async def async_will_remove_from_hass(self) -> None:
        if self._remove_time_tracker_fn:
            self._remove_time_tracker_fn()

    async def _async_historical_handle_update(self) -> None:
        await self.async_update_historical()
        await self.async_write_ha_historical_states()


def local_dt_from_timestamp(ts: float):
    return dtutil.as_local(dtutil.utc_from_timestamp(ts))
