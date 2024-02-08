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
import itertools
from collections.abc import Iterator
from dataclasses import asdict, dataclass, field
from math import ceil
from typing import Any


@dataclass
class HistoricalState:
    state: Any
    ts: float
    attributes: dict[str, Any] = field(default_factory=dict)

    def asdict(self):
        return asdict(self)


def group_by_interval(
    historical_states: list[HistoricalState], **blockize_kwargs
) -> Iterator[Any]:
    fn = functools.partial(blockize, **blockize_kwargs)
    yield from itertools.groupby(historical_states, key=lambda x: fn)


def blockize(
    hist_state: HistoricalState,
    *,
    granurality: int = 60 * 60,
    border_in_previous_block: int = True,
) -> int:
    ts = ceil(hist_state.ts)
    block = ts // granurality
    leftover = ts % granurality

    if border_in_previous_block and leftover == 0:
        block = block - 1

    return block * granurality
