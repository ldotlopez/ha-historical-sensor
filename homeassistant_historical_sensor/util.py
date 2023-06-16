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
from typing import List, Optional

import sqlalchemy.exc
from homeassistant.components import recorder
from homeassistant.components.recorder import Recorder
from homeassistant.components.recorder import db_schema as db_schema
from homeassistant.components.recorder.statistics import (
    StatisticsRow,
    get_last_statistics,
)
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from sqlalchemy import and_, delete, not_, or_, select
from sqlalchemy.orm import Session

_LOGGER = logging.getLogger(__name__)


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


def get_states_meta(session: Session, entity_id: str) -> db_schema.StatesMeta:
    ret = session.execute(_get_base_stmt(session, entity_id)).scalar()

    if not ret:
        ret = db_schema.StatesMeta(entity_id=entity_id)
        session.add(ret)
        session.commit()

    return ret


def _get_base_stmt(session: Session, entity_id: str):
    return (
        select(db_schema.States)
        .join(db_schema.StatesMeta)
        .where(db_schema.StatesMeta.entity_id == entity_id)
    )


def delete_invalid_states(session: Session, entity_id: str):
    stmt = _get_base_stmt(session, entity_id).where(
        or_(
            db_schema.States.state == STATE_UNKNOWN,
            db_schema.States.state == STATE_UNAVAILABLE,
        )
    )
    states = session.execute(stmt).scalars().fetchall()

    n_states = len(states)

    for state in states:
        session.delete(state)
    session.commit()

    return n_states


def get_latest_state(session: Session, entity_id: str):
    stmt = (
        _get_base_stmt(session, entity_id)
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
