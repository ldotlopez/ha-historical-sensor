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


import math
import sys
from typing import Any

from homeassistant.const import (
    ATTR_ASSUMED_STATE,
    ATTR_ATTRIBUTION,
    ATTR_DEVICE_CLASS,
    ATTR_ENTITY_PICTURE,
    ATTR_FRIENDLY_NAME,
    ATTR_ICON,
    ATTR_SUPPORTED_FEATURES,
    ATTR_UNIT_OF_MEASUREMENT,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.helpers.entity import Entity

FLOAT_PRECISION = abs(int(math.floor(math.log10(abs(sys.float_info.epsilon))))) - 1


# Modified version of
# homeassistant.helpers.entity.Entity._stringify_state
# https://github.com/home-assistant/core/blob/dev/homeassistant/helpers/entity.py
def _stringify_state(self: Entity, state: Any) -> str:
    """Convert state to string."""
    # Historical sensors are usually unavailable, ignore current state, handle only
    # state availability
    if not self.available:
        return STATE_UNAVAILABLE
    if state is None:
        return STATE_UNKNOWN
    if isinstance(state, float):
        # If the entity's state is a float, limit precision according to machine
        # epsilon to make the string representation readable
        return f"{state:.{FLOAT_PRECISION}}"
    return str(state)


# Code extracted and modified from
# homeassistant.helpers.entity.Entity._async_generate_attributes
# https://github.com/home-assistant/core/blob/dev/homeassistant/helpers/entity.py
def _build_attributes(self: Entity) -> dict[str, Any]:
    """Calculate state string and attribute mapping."""
    entry = self.registry_entry

    attr = self.capability_attributes
    attr = dict(attr) if attr else {}

    available = self.available  # only call self.available once per update cycle
    if available:
        attr.update(self.state_attributes or {})
        attr.update(self.extra_state_attributes or {})

    if (unit_of_measurement := self.unit_of_measurement) is not None:
        attr[ATTR_UNIT_OF_MEASUREMENT] = unit_of_measurement

    if assumed_state := self.assumed_state:
        attr[ATTR_ASSUMED_STATE] = assumed_state

    if (attribution := self.attribution) is not None:
        attr[ATTR_ATTRIBUTION] = attribution

    if (
        device_class := (entry and entry.device_class) or self.device_class
    ) is not None:
        attr[ATTR_DEVICE_CLASS] = str(device_class)

    if (entity_picture := self.entity_picture) is not None:
        attr[ATTR_ENTITY_PICTURE] = entity_picture

    if (icon := (entry and entry.icon) or self.icon) is not None:
        attr[ATTR_ICON] = icon

    if (name := (entry and entry.name) or self._friendly_name_internal()) is not None:
        attr[ATTR_FRIENDLY_NAME] = name

    if (supported_features := self.supported_features) is not None:
        attr[ATTR_SUPPORTED_FEATURES] = supported_features

    return attr
