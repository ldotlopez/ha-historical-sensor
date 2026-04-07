#!/usr/bin/env python3

import functools
import itertools
import logging
from collections.abc import Iterator
from dataclasses import asdict, dataclass, field
from math import ceil
from typing import Any, Literal

from homeassistant.components import recorder
from homeassistant.components.recorder.models import StatisticMetaData
from homeassistant.components.recorder.statistics import (
    StatisticsRow,
    get_last_statistics,
)
from homeassistant.const import MAJOR_VERSION, MINOR_VERSION
from homeassistant.const import __version__ as HA_FULL_VERSION
from homeassistant.core import HomeAssistant

LOGGER = logging.getLogger(__name__)


@dataclass
class HistoricalState:
    state: Any
    timestamp: float
    attributes: dict[str, Any] = field(default_factory=dict)

    def asdict(self):
        return asdict(self)


def group_by_interval(
    historical_states: list[HistoricalState], **blockize_kwargs
) -> Iterator[Any]:
    fn = functools.partial(blockize, **blockize_kwargs)
    sorted_states = sorted(historical_states, key=fn)
    yield from itertools.groupby(sorted_states, key=fn)


def blockize(
    historical_states: HistoricalState,
    *,
    granularity: int = 60 * 60,
    border_in_previous_block: bool = True,
) -> int:
    ts = ceil(historical_states.timestamp)
    block = ts // granularity
    leftover = ts % granularity
    if border_in_previous_block and leftover == 0:
        block = block - 1
    return block * granularity


async def hass_get_last_statistic(
    hass: HomeAssistant,
    statistics_metadata: StatisticMetaData,
    *,
    convert_units: bool = True,
    types: (
        set[Literal["last_reset", "max", "mean", "min", "state", "sum"]] | None
    ) = None,
) -> StatisticsRow | None:
    if types is None:
        types = {"last_reset", "max", "mean", "min", "state", "sum"}

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
