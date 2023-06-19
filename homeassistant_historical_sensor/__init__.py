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

from homeassistant.const import (
    MAJOR_VERSION,
    MINOR_VERSION,
    __version__ as HA_FULL_VERSION,
)

from .sensor import HistoricalSensor, PollUpdateMixin
from .state import HistoricalState
from .consts import MIN_REQ_MAJOR_VERSION, MIN_REQ_MINOR_VERSION

LOGGER = logging.getLogger(__name__)

if not (
    (MAJOR_VERSION >= MIN_REQ_MAJOR_VERSION)
    and (MINOR_VERSION >= MIN_REQ_MINOR_VERSION)
):
    msg = (
        f"Running HomeAssistant {HA_FULL_VERSION}, "
        f"Minimum required version >={MIN_REQ_MAJOR_VERSION}.{MIN_REQ_MINOR_VERSION}.0"
    )
    LOGGER.debug(msg)
    raise SystemError(msg)

__all__ = [
    "HistoricalSensor",
    "HistoricalState",
    "PollUpdateMixin",
]
