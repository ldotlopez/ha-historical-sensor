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
from contextlib import contextmanager
from typing import List, Optional

from homeassistant.components import recorder
from homeassistant.components.recorder import db_schema
from homeassistant.components.recorder.statistics import (
    StatisticsRow,
    get_last_statistics,
)
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from sqlalchemy import Select, not_, or_, select
from sqlalchemy.orm import Session

_LOGGER = logging.getLogger(__name__)


@contextmanager
def hass_recorder_session(hass: HomeAssistant):
    r = recorder.get_instance(hass)
    with recorder.util.session_scope(session=r.get_session()) as session:
        yield session


async def get_last_statistics_wrapper(
    hass: HomeAssistant, statistic_id: str
) -> Optional[StatisticsRow]:
    res = await recorder.get_instance(hass).async_add_executor_job(
        get_last_statistics,
        hass,
        1,
        statistic_id,
        True,
        set(["last_reset", "max", "mean", "min", "state", "sum"]),
    )
    if not res:
        return None

    return res[statistic_id][0]


def _entity_id_states_stmt(session: Session, entity: Entity) -> Select:
    return (
        select(db_schema.States)
        .join(db_schema.StatesMeta)
        .where(db_schema.StatesMeta.entity_id == entity.entity_id)
    )


def get_entity_states_meta(session: Session, entity: Entity) -> db_schema.StatesMeta:
    res = session.execute(_entity_id_states_stmt(session, entity)).scalar()

    if res:
        return res.states_meta_rel

    else:
        ret = db_schema.StatesMeta(entity_id=entity.entity_id)
        session.add(ret)
        session.commit()

        return ret


def delete_entity_invalid_states(session: Session, entity: Entity) -> int:
    stmt = _entity_id_states_stmt(session, entity).order_by(
        db_schema.States.last_updated_ts.asc()
    )

    prev = None
    to_delete = []

    for state in session.execute(stmt).scalars():
        if state.state in [STATE_UNKNOWN, STATE_UNAVAILABLE]:
            to_delete.append(state)
        else:
            state.old_state_id = prev.state_id if prev else None  # type: ignore[attr-defined]
            session.add(state)
            prev = state

    for state in to_delete:
        session.delete(state)

    session.commit()

    return len(to_delete)


def get_entity_latest_state(session: Session, entity: Entity):
    stmt = (
        _entity_id_states_stmt(session, entity)
        .where(
            not_(
                or_(
                    db_schema.States.state == STATE_UNAVAILABLE,
                    db_schema.States.state == STATE_UNKNOWN,
                )
            )
        )
        .order_by(db_schema.States.last_updated_ts.desc())
    )
    return session.execute(stmt).scalar()


def save_states(session: Session, states: List[db_schema.States]):
    session.add_all(states)
    session.commit()
