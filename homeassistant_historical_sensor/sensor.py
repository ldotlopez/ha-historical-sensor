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
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

import sqlalchemy.exc
import sqlalchemy.orm
from homeassistant.components import recorder
from homeassistant.components.recorder import db_schema as db_schema
from homeassistant.components.recorder.models import StatisticData, StatisticMetaData
from homeassistant.components.recorder.statistics import (
    async_add_external_statistics,
    async_import_statistics,
    split_statistic_id,
    valid_statistic_id,
    clear_statistics,
    list_statistic_ids,
    get_last_statistics,
)
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util
from sqlalchemy import not_, or_

from .patches import _build_attributes, _stringify_state

_LOGGER = logging.getLogger(__name__)
RECORDER_SOURCE = "recorder"


@dataclass
class DatedState:
    state: Any
    when: datetime
    attributes: Dict[str, Any] = field(default_factory=dict)


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
        self._attr_historical_states: List[DatedState] = []  # type: ignore[annotation-unchecked]

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
    def statistics_enabled(self):
        if hasattr(self, "_attr_statistics_enabled"):
            return self._attr_statistics_enabled

        smd = self.get_statatistics_metadata()
        enabled = smd["has_mean"] or smd["has_sum"]
        return enabled

    @abstractmethod
    async def async_update_historical(self):
        """async_update_historical()

        Implement this async method to fetch historical data from provider and store
        into self._attr_historical_states
        """
        raise NotImplementedError()

    async def async_write_ha_historical_states(self):
        """async_write_ha_historical_states()

        This method writes `self.historical_states` into database
        """

        def _normalize_dated_state_when(st):
            if not isinstance(st, DatedState):
                return None

            if st.when.tzinfo is None:
                st.when = dt_util.as_local(st.when)

            if st.when.tzinfo is not timezone.utc:
                st.when = dt_util.as_utc(st.when)

            return st

        dated_states = self.historical_states
        dated_states = (_normalize_dated_state_when(x) for x in dated_states)
        dated_states = (x for x in dated_states if x is not None)
        dated_states = list(sorted(dated_states, key=lambda x: x.when))

        _LOGGER.debug(
            f"{self.entity_id}: {len(dated_states)} historical states available"
        )

        if not dated_states:
            return

        self._get_recorder_instance().async_add_executor_job(
            self._save_states_into_recorder, dated_states
        )

        if self.statistics_enabled:
            await self._async_save_states_into_statistics(dated_states)
        else:
            _LOGGER.debug(f"{self.entity_id}: statistics are not enabled")

    def _get_recorder_instance(self):
        return recorder.get_instance(self.hass)

    async def _async_save_states_into_statistics(self, dated_states: List[DatedState]):
        # def delete_statistics():
        #     with recorder.util.session_scope(
        #         session=self._get_recorder_instance().get_session()
        #     ) as session:
        #         start_cutoff = dated_states[0].when - timedelta(hours=1)
        #         end_cutoff = dated_states[-1].when
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

        #     clear_statistics(self._get_recorder_instance(), stats)
        #     _LOGGER.debug(f"Cleared {len(stats)} statistics")

        # await self._get_recorder_instance().async_add_executor_job(delete_statistics)

        statistics_meta = self.get_statatistics_metadata()

        def get_cutoff(*args, **kwargs):
            res = get_last_statistics(
                hass=self.hass,
                number_of_stats=1,
                statistic_id=statistics_meta["statistic_id"],
                convert_units=True,
                types=set(["last_reset", "max", "mean", "min", "state", "sum"]),
            )
            try:
                return res[statistics_meta["statistic_id"]][0]["start"]
            except (KeyError, IndexError):
                return None

        cutoff = await self._get_recorder_instance().async_add_executor_job(get_cutoff)
        if cutoff is not None:
            cutoff = cutoff + timedelta(hours=1)
            dated_states = [x for x in dated_states if x.when > cutoff]

        is_external = valid_statistic_id(statistics_meta["statistic_id"])
        if is_external:
            fn = async_add_external_statistics
        else:
            fn = async_import_statistics

        statistics_data = await self.async_calculate_statistic_data(dated_states)

        fn(self.hass, statistics_meta, statistics_data)
        _LOGGER.debug(
            f"{self.entity_id}: collected {len(statistics_data)} statistic points"
        )

    def _save_states_into_recorder(self, dated_states: List[DatedState]):
        #
        # 2023.2.1 Introduces last_updated_ts, last_changed_ts columns
        #

        with recorder.util.session_scope(
            session=self._get_recorder_instance().get_session()
        ) as session:
            base_qs = session.query(db_schema.States).filter(
                db_schema.States.entity_id == self.entity_id
            )

            #
            # Delete invalid states
            #
            try:
                states = base_qs.filter(
                    or_(
                        db_schema.States.state == STATE_UNKNOWN,
                        db_schema.States.state == STATE_UNAVAILABLE,
                    )
                )
                state_count = states.count()
                states.delete()
                session.commit()

                _LOGGER.debug(f"Deleted {state_count} invalid states")

            except sqlalchemy.exc.IntegrityError:
                session.rollback()
                _LOGGER.debug("Warning: Current recorder schema is not supported")
                _LOGGER.debug(
                    "Invalid states can't be deleted from recorder."
                    + "This is not critical just unsightly for some graphs "
                )

            #
            # Delete intersecting states
            #
            cutoff = dt_util.as_timestamp(dated_states[0].when)
            intersect_states = base_qs.filter(
                db_schema.States.last_updated_ts >= cutoff
            )
            intersect_count = intersect_states.count()
            intersect_states.delete()
            session.commit()

            _LOGGER.debug(
                f"Deleted {intersect_count} states after {dated_states[0].when}"
            )

            #
            # Check latest state in the database
            #
            latest_state = base_qs.order_by(
                db_schema.States.last_updated.desc()
            ).first()

            #
            # Build recorder State, StateAttributes and Event
            #

            db_states: List[db_schema.States] = []

            for idx, dt_st in enumerate(dated_states):
                attrs_as_dict = _build_attributes(self, dt_st.state)
                attrs_as_dict.update(dt_st.attributes)
                attrs_as_str = db_schema.JSON_DUMP(attrs_as_dict)

                attrs_as_bytes = (
                    b"{}" if dt_st.state is None else attrs_as_str.encode("utf-8")
                )

                attrs_hash = db_schema.StateAttributes.hash_shared_attrs_bytes(
                    attrs_as_bytes
                )

                state_attributes = db_schema.StateAttributes(
                    hash=attrs_hash, shared_attrs=attrs_as_str
                )

                when_as_ts = dt_util.as_timestamp(dt_st.when)
                state = db_schema.States(
                    entity_id=self.entity_id,
                    last_changed_ts=when_as_ts,
                    last_updated_ts=when_as_ts,
                    old_state=db_states[idx - 1] if idx else latest_state,
                    state=_stringify_state(self, dt_st.state),
                    state_attributes=state_attributes,
                )
                _LOGGER.debug(f" => {state.state} @ {dt_st.when}")
                db_states.append(state)

            session.add_all(db_states)
            session.commit()

            _LOGGER.debug(f"{self.entity_id}: {len(db_states)} saved into the database")

    def get_statatistics_metadata(self) -> StatisticMetaData:
        as_native = getattr(self, "device_class", None) and getattr(
            self, "state_class", None
        )

        if as_native:
            statistic_id = self.entity_id
            source = RECORDER_SOURCE
        else:
            statistic_id = statistic_id = self.entity_id.replace(".", ":")
            source = split_statistic_id(statistic_id)[0]

        metadata = StatisticMetaData(
            has_mean=False,
            has_sum=False,
            name=f"{self.name} Statistics",
            source=source,
            statistic_id=statistic_id,
            unit_of_measurement=self.unit_of_measurement,
        )

        return metadata

    async def async_calculate_statistic_data(
        self, dated_states: List[DatedState]
    ) -> List[StatisticData]:
        """Calculate statistics data from dated states

        This method should be implemented by sensors
        """
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
