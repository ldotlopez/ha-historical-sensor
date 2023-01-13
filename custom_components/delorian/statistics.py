import logging
from datetime import datetime
from typing import Any

import homeassistant.components.recorder.util as recorder_util
from homeassistant.components.recorder.const import DATA_INSTANCE
from homeassistant.components.recorder.models import StatisticData, StatisticMetaData
from homeassistant.components.recorder.statistics import (
    async_add_external_statistics,
    clear_statistics,
    get_last_statistics,
    list_statistic_ids,
    statistics_during_period,
)
from homeassistant.const import CURRENCY_EURO, ENERGY_KILO_WATT_HOUR, POWER_KILO_WATT
from homeassistant.util import dt as dt_util

from . import const
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class StatisticsHelper:
    async def _add_statistics(self, new_stats):
        """Add new statistics"""

        for scope in new_stats:
            if scope in self.consumption_stats:
                metadata = StatisticMetaData(
                    has_mean=False,
                    has_sum=True,
                    name=const.STAT_TITLE_KWH(self.id, scope),
                    source=const.DOMAIN,
                    statistic_id=self.sid[scope],
                    unit_of_measurement=ENERGY_KILO_WATT_HOUR,
                )
            elif scope in self.cost_stats:
                metadata = StatisticMetaData(
                    has_mean=False,
                    has_sum=True,
                    name=const.STAT_TITLE_EUR(self.id, scope),
                    source=const.DOMAIN,
                    statistic_id=self.sid[scope],
                    unit_of_measurement=CURRENCY_EURO,
                )
            elif scope in self.maximeter_stats:
                metadata = StatisticMetaData(
                    has_mean=True,
                    has_sum=False,
                    name=const.STAT_TITLE_KW(self.id, scope),
                    source=const.DOMAIN,
                    statistic_id=self.sid[scope],
                    unit_of_measurement=POWER_KILO_WATT,
                )
            else:
                break
            async_add_external_statistics(self.hass, metadata, new_stats[scope])
