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


from typing import Optional
from homeassistant.components import recorder
from homeassistant.core import HomeAssistant
from homeassistant.components.recorder.statistics import get_last_statistics


async def get_last_statistics_wrapper(
    hass: HomeAssistant, statistic_id: str
) -> Optional[dict]:
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
