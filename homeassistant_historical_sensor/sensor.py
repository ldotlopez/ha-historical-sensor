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


import functools
import logging
from abc import abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import sqlalchemy.exc
import sqlalchemy.orm
from homeassistant.components import recorder
from homeassistant.components.recorder import db_schema as rec_db_schema
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util
from sqlalchemy import not_, or_

from .patches import _build_attributes, _stringify_state

_LOGGER = logging.getLogger(__name__)


@dataclass
class DatedState:
    state: Any
    when: datetime
    attributes: Dict[str, Any] = field(default_factory=dict)


# You must know:
# * DB keeps datetime object as utc
# * Each time hass is started a new record is created, that record can be 'unknow'
#   or 'unavailable'


class HistoricalSensor:
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
        self._attr_historical_states = []

    async def async_added_to_hass(self) -> None:
        if self.should_poll:
            raise Exception("poll model is not supported")

    @property
    def should_poll(self):
        # HistoricalSensors MUST NOT poll.
        # Polling creates incorrect states at intermediate time points.

        return False

    # @property
    # def available(self):
    #     # Leave us alone!
    #     return False

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
        else:
            return []

    @abstractmethod
    async def async_update_historical(self):
        """async_update_historical()

        Implement this async method to fetch historical data from provider and store
        into self._attr_historical_states
        """
        raise NotImplementedError()

    def async_write_ha_historical_states(self):
        """async_write_ha_historical_states()

        This method writes `self.historical_states` into database
        """

        def _normalize_time_state(st):
            if not isinstance(st, DatedState):
                return None

            if st.when.tzinfo is None:
                st.when = dt_util.as_local(st.when)

            if st.when.tzinfo is not timezone.utc:
                st.when = dt_util.as_utc(st.when)

            return st

        dated_states = self.historical_states
        dated_states = [_normalize_time_state(x) for x in dated_states]
        dated_states = [x for x in dated_states if x is not None]
        dated_states = list(sorted(dated_states, key=lambda x: x.when))

        _LOGGER.debug(
            f"{self.entity_id}: {len(dated_states)} historical states available"
        )

        if not dated_states:
            return

        fn = functools.partial(self._save_states_into_recorder, dated_states)
        self._get_recorder_instance().async_add_executor_job(fn)

    def _get_recorder_instance(self):
        return recorder.get_instance(self.hass)

    def _save_states_into_recorder(self, dated_states):
        #
        # Cleanup invalid states in database
        #
        with recorder.util.session_scope(
            session=self._get_recorder_instance().get_session()
        ) as session:
            try:
                self._delete_invalid_states(session)
                session.commit()

            except sqlalchemy.exc.IntegrityError:
                session.rollback()
                _LOGGER.debug("Warning: Current recorder schema is not supported")
                _LOGGER.debug(
                    "Invalid states can't be deleted from recorder."
                    + "This is not critical just unsightly for some graphs "
                )

        #
        # Write states to recorder
        #
        with recorder.util.session_scope(
            session=self._get_recorder_instance().get_session()
        ) as session:
            #
            # Check latest state in the database
            #
            latest_db_state = (
                session.query(rec_db_schema.States)
                .filter(rec_db_schema.States.entity_id == self.entity_id)
                .filter(
                    not_(
                        or_(
                            rec_db_schema.States.state == "unknown",
                            rec_db_schema.States.state == "unavailable",
                        )
                    )
                )
                .order_by(rec_db_schema.States.last_updated.desc())
                .first()
            )
            # first_run = latest_db_state is None

            #
            # Drop historical states older than lastest db state
            #
            dated_states = list(sorted(dated_states, key=lambda x: x.when))
            if latest_db_state:
                # Fix TZINFO from database
                cutoff = latest_db_state.last_updated.replace(tzinfo=timezone.utc)
                _LOGGER.debug(
                    f"{self.entity_id}: found previous states in db "
                    + f"(latest is dated at: {cutoff}, value:{latest_db_state.state})"
                )
                dated_states = [x for x in dated_states if x.when > cutoff]

            if not dated_states:
                _LOGGER.debug(f"{self.entity_id}: no new states")
                return

            _LOGGER.debug(
                f"{self.entity_id}: {len(dated_states)} states pass the cutoff, "
                + f"extending from {dated_states[0].when} to {dated_states[-1].when}"
            )

            #
            # Build recorder State, StateAttributes and Event
            #

            db_states = []
            for idx, dt_st in enumerate(dated_states):
                attrs_as_dict = _build_attributes(self, dt_st.state)
                attrs_as_dict.update(dt_st.attributes)
                attrs_as_str = rec_db_schema.JSON_DUMP(attrs_as_dict)

                attrs_as_bytes = (
                    b"{}" if dt_st.state is None else attrs_as_str.encode("utf-8")
                )

                attrs_hash = rec_db_schema.StateAttributes.hash_shared_attrs_bytes(
                    attrs_as_bytes
                )

                state_attributes = rec_db_schema.StateAttributes(
                    hash=attrs_hash, shared_attrs=attrs_as_str
                )

                state = rec_db_schema.States(
                    entity_id=self.entity_id,
                    last_changed=dt_st.when,
                    last_updated=dt_st.when,
                    old_state=db_states[idx - 1] if idx else latest_db_state,
                    state=_stringify_state(self, dt_st.state),
                    state_attributes=state_attributes,
                )
                _LOGGER.debug(f" => {state.state} @ {state.last_changed}")
                db_states.append(state)

            session.add_all(db_states)
            session.commit()

            _LOGGER.debug(f"{self.entity_id}: {len(db_states)} saved into the database")

    def _delete_invalid_states(self, session: sqlalchemy.orm.session.Session):
        states = (
            session.query(rec_db_schema.States)
            .filter(rec_db_schema.States.entity_id == self.entity_id)
            .filter(
                or_(
                    rec_db_schema.States.state == STATE_UNKNOWN,
                    rec_db_schema.States.state == STATE_UNAVAILABLE,
                )
            )
        )
        n_states = states.count()

        # Deleting StateAttributes raises IntegrityError :shrug:
        # states_attrs = session.query(rec_db_schema.StateAttributes).filter(
        #     rec_db_schema.StateAttributes.attributes_id.in_(
        #         (x.attributes_id for x in states)
        #     )
        # )
        # states_attrs.delete()

        states.delete()

        if n_states:
            _LOGGER.debug(f"{self.entity_id}: deleted {n_states} invalid states")

        ##
        # Strategy: delete orphan StateAttributes
        # This implementation is broken, we can end deleting states from other
        # integrations
        ##

        # attr_ids_from_states = (
        #     x.attributes_id
        #     for x in session.query(rec_db_schema.States)
        # )

        # attrs_ids_from_state_attrs = (
        #     x.attributes_id
        #     for x in session.query(rec_db_schema.StateAttributes)
        # )

        # orphan_attr_ids = set(attrs_ids_from_state_attrs) - set(attr_ids_from_states)

        # session.query(rec_db_schema.StateAttributes).filter(
        #     rec_db_schema.StateAttributes.attributes_id.in_(orphan_attr_ids)
        # ).delete()

        ##
        # End strategy: delete orphan StateAttributes
        ##


class PollUpdateMixin(Entity):
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

        _LOGGER.debug(f"{self.entity_id}: added to hass, do initial update")  # type: ignore[attr-defined]
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
        self._remove_time_tracker_fn()

    async def _async_historical_handle_update(self) -> None:
        await self.async_update_historical()
        self.async_write_ha_historical_states()
