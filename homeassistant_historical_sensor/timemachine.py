#!/usr/bin/env python3

import logging
from contextlib import contextmanager
from typing import Literal, cast

from homeassistant.components import recorder
from homeassistant.components.recorder import Recorder, db_schema
from homeassistant.components.recorder.models import StatisticData, StatisticMetaData
from homeassistant.components.recorder.statistics import (
    StatisticsRow,
    get_last_statistics,
)
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from sqlalchemy import Select, and_, not_, or_, select
from sqlalchemy.orm import Session

_LOGGER = logging.getLogger(__name__)


@contextmanager
def hass_recorder_session(hass: HomeAssistant):
    r = recorder.get_instance(hass)
    with recorder_session(r) as session:
        yield session


@contextmanager
def recorder_session(rec: Recorder):
    with recorder.util.session_scope(session=rec.get_session()) as session:
        yield session


async def hass_get_entity_states_metadata_id(
    hass: HomeAssistant, entity: Entity
) -> int | None:
    r = recorder.get_instance(hass)
    return await r.async_add_executor_job(
        recorder_get_entity_states_metadata_id, r, entity.entity_id
    )


def recorder_get_entity_states_metadata_id(rec: Recorder, entity_id: str) -> int | None:
    with recorder_session(rec) as sess:
        return rec.states_meta_manager.get(entity_id, sess, True)


def get_states_meta(session: Session, entity_id: str) -> db_schema.StatesMeta:
    stmt = select(db_schema.StatesMeta).where(
        db_schema.StatesMeta.entity_id == entity_id
    )

    return session.execute(stmt).scalar_one()


async def hass_get_last_statistic(
    hass: HomeAssistant,
    statistics_metadata: StatisticMetaData,
    *,
    convert_units: bool = True,
    types: set[Literal["last_reset", "max", "mean", "min", "state", "sum"]] = {
        "last_reset",
        "max",
        "mean",
        "min",
        "state",
        "sum",
    },
) -> StatisticsRow | None:
    res = await recorder.get_instance(hass).async_add_executor_job(
        get_last_statistics,
        hass,
        1,
        statistics_metadata["statistic_id"],
        convert_units,
        types,
    )
    if not res:
        return None

    return res[statistics_metadata["statistic_id"]][0]


def _build_entity_states_stmt(entity: Entity) -> Select:
    return (
        select(db_schema.States)
        .join(db_schema.StatesMeta)
        .where(db_schema.StatesMeta.entity_id == entity.entity_id)
    )


def _rebuild_states_chain(
    session: Session, entity: Entity, *, since: float = 0
) -> None:
    stmt = _build_entity_states_stmt(entity).order_by(
        db_schema.States.last_updated_ts.asc()
    )

    if since:
        prev = get_last_state(session, entity, before=since)

    else:
        prev = None

    for state in session.execute(stmt).scalars():
        state.old_state_id = prev.state_id if prev else None
        prev = state


def delete_invalid_states(session: Session, entity: Entity) -> list[db_schema.States]:
    stmt = _build_entity_states_stmt(entity)
    stmt = stmt.where(db_schema.States.state.in_([STATE_UNKNOWN, STATE_UNAVAILABLE]))

    deleted_states = list(session.execute(stmt).scalars())
    for state in deleted_states:
        session.delete(state)

    _rebuild_states_chain(session, entity)

    return deleted_states


def delete_states_in_period(
    session: Session, entity: Entity, *, start: float, end: float
) -> list[db_schema.States]:
    """
    Delete all states between two points in time
    """

    # Link states just outside the period

    first_state_after_end = session.execute(
        _build_entity_states_stmt(entity).where(db_schema.States.last_updated_ts > end)
    ).scalar()

    last_state_before_start = session.execute(
        _build_entity_states_stmt(entity).where(
            db_schema.States.last_updated_ts < start
        )
    ).scalar()

    if first_state_after_end:
        first_state_after_end.old_state_id = (
            last_state_before_start.state_id if last_state_before_start else None
        )

    # Execute deletion backwards in time to delink safely the chain

    delete_stmt = _build_entity_states_stmt(entity)
    delete_stmt = delete_stmt.where(
        and_(
            db_schema.States.last_updated_ts >= start,
            db_schema.States.last_updated_ts <= end,
        )
    ).order_by(db_schema.States.last_updated_ts.desc())

    deleted_states = cast(
        list[db_schema.States], list(session.execute(delete_stmt).scalars())
    )

    for state in deleted_states:
        session.delete(state)

    return deleted_states


def get_last_state(
    session: Session, entity: Entity, *, before: float | None = None
) -> db_schema.States:
    """
    Get last state from database
    If `before` is passed the lastest state will be the last previous to the time
    specified in `before`
    """
    stmt = _build_entity_states_stmt(entity)
    if before:
        stmt = stmt.where(db_schema.States.last_updated_ts < before)

    stmt = stmt.where(
        not_(
            or_(
                db_schema.States.state == STATE_UNAVAILABLE,
                db_schema.States.state == STATE_UNKNOWN,
            )
        )
    ).order_by(db_schema.States.last_updated_ts.desc())

    state = cast(db_schema.States, session.execute(stmt).scalar())

    return state


def save_states(
    session: Session,
    entity: Entity,
    states: list[db_schema.States],
    *,
    overwrite_overlaping: bool = False,
) -> list[db_schema.States]:
    # Initial checks:
    # - at least one state
    # - states meta information available

    if not states:
        return []

    states_meta = get_states_meta(session, entity.entity_id)
    if not states_meta:
        _LOGGER.error(
            f"{entity.entity_id}: "
            + "states meta information is NOT available (it should be!). This is a bug"
        )
        return []

    # Ensure ordered data

    states = list(sorted(states, key=lambda x: x.last_updated_ts))

    # Add some data to states

    for x in states:
        x.states_meta_rel = states_meta
        x.metadata_id = states_meta.metadata_id
        x.entity_id = states_meta.entity_id

        assert x.last_updated_ts is not None

    # Handle overlaping states

    if overwrite_overlaping:
        deleted = delete_states_in_period(
            session,
            entity,
            start=states[0].last_updated_ts,
            end=states[-1].last_updated_ts,
        )
        _LOGGER.debug(
            f"{entity.entity_id}: deleted {len(deleted)} overlaping exisisting states"
        )

    else:
        last_existing_state = get_last_state(session, entity)
        assert last_existing_state.last_updated_ts is not None

        if last_existing_state:
            n_prev = len(states)
            states = [
                x
                for x in states
                if x.last_updated_ts > last_existing_state.last_updated_ts
            ]
            n_post = len(states)

            _LOGGER.debug(
                f"{entity.entity_id}: discarded {n_prev-n_post} overlaping new states"
            )

    if not states:
        return []

    # Insert states and rebuild chain

    for state in states:
        session.add(state)

    _rebuild_states_chain(session, entity, since=states[0].last_updated_ts)

    return states


def delete_statistics_since(
    session: Session,
    statistic_id: str,
    *,
    since: float,
) -> list[db_schema.Statistics]:
    # SELECT *
    # FROM statistics LEFT OUTER JOIN statistics_meta
    # ON statistics.metadata_id = statistics_meta.id
    # WHERE statistics_meta.statistic_id = 'sensor.delorian';

    stmt = (
        select(db_schema.Statistics)
        .join(
            db_schema.StatisticsMeta,
            db_schema.Statistics.metadata_id == db_schema.StatisticsMeta.id,
            isouter=True,
        )
        .filter(db_schema.StatisticsMeta.statistic_id == statistic_id)
        .filter(db_schema.Statistics.start_ts >= since)
    )

    deleted_statistics = list(x for x in session.execute(stmt).scalars())
    for x in deleted_statistics:
        session.delete(x)

    return deleted_statistics


def save_statistics_data(
    session: Session,
    statistics_metadata: StatisticMetaData,
    statistics_data: list[StatisticData],
    *,
    overwrite_overlaping: bool = False,
):
    raise NotImplementedError()
    return []
