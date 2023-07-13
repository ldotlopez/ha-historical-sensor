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


from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

from homeassistant.util import dt as dtutil


@dataclass
class HistoricalState:
    state: Any
    dt: datetime
    attributes: dict[str, Any] = field(default_factory=dict)

    def asdict(self):
        return asdict(self)

    def as_value_and_timestamp(self):
        if not self.dt.tzinfo:
            raise ValueError(f"{self}.dt is missing tzinfo")

        utc = dtutil.as_utc(self.dt)
        ts = dtutil.utc_to_timestamp(utc)
        return self.state, ts
