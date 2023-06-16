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

from homeassistant.const import MAJOR_VERSION, MINOR_VERSION

from .sensor import HistoricalSensor, PollUpdateMixin
from .state import HistoricalState

LOGGER = logging.getLogger(__name__)

if not (MAJOR_VERSION >= 2023 and MINOR_VERSION >= 6):
    msg = "Required homeassistant version >=2023.6.0"
    LOGGER.debug(msg)
    raise SystemError(msg)

__all__ = [
    "HistoricalSensor",
    "HistoricalState",
    "PollUpdateMixin",
]
