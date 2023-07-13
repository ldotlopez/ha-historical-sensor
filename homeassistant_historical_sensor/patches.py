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

from homeassistant.config import DATA_CUSTOMIZE
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
    TEMP_CELSIUS,
    TEMP_FAHRENHEIT,
)
from homeassistant.helpers.entity import Entity

FLOAT_PRECISION = abs(int(math.floor(math.log10(abs(sys.float_info.epsilon))))) - 1


# Modified version of
# homeassistant.helpers.entity.Entity._stringify_state
# https://github.com/home-assistant/core/blob/dev/homeassistant/helpers/entity.py


def _stringify_state(self: Entity, state: Any) -> str:
    """Convert state to string."""
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
# homeassistant.helpers.entity.Entity._async_write_ha_state
# https://github.com/home-assistant/core/blob/dev/homeassistant/helpers/entity.py


def _build_attributes(self: Entity, state: Any) -> dict[str, str]:
    attr = self.capability_attributes
    attr = dict(attr) if attr else {}

    state = _stringify_state(self, state)
    if self.available:
        attr.update(self.state_attributes or {})
        extra_state_attributes = self.extra_state_attributes
        # Backwards compatibility for "device_state_attributes" deprecated in 2021.4
        # Add warning in 2021.6, remove in 2021.10
        if extra_state_attributes is None:
            extra_state_attributes = self.device_state_attributes
        attr.update(extra_state_attributes or {})

    unit_of_measurement = self.unit_of_measurement
    if unit_of_measurement is not None:
        attr[ATTR_UNIT_OF_MEASUREMENT] = unit_of_measurement

    entry = self.registry_entry
    # pylint: disable=consider-using-ternary
    if (name := (entry and entry.name) or self.name) is not None:
        attr[ATTR_FRIENDLY_NAME] = name

    if (icon := (entry and entry.icon) or self.icon) is not None:
        attr[ATTR_ICON] = icon

    if (entity_picture := self.entity_picture) is not None:
        attr[ATTR_ENTITY_PICTURE] = entity_picture

    if assumed_state := self.assumed_state:
        attr[ATTR_ASSUMED_STATE] = assumed_state

    if (supported_features := self.supported_features) is not None:
        attr[ATTR_SUPPORTED_FEATURES] = supported_features

    if (device_class := self.device_class) is not None:
        attr[ATTR_DEVICE_CLASS] = str(device_class)

    if (attribution := self.attribution) is not None:
        attr[ATTR_ATTRIBUTION] = attribution

    # Overwrite properties that have been set in the config file.
    if DATA_CUSTOMIZE in self.hass.data:
        attr.update(self.hass.data[DATA_CUSTOMIZE].get(self.entity_id))

    # Convert temperature if we detect one
    try:
        unit_of_measure = attr.get(ATTR_UNIT_OF_MEASUREMENT)
        units = self.hass.config.units
        if (
            unit_of_measure in (TEMP_CELSIUS, TEMP_FAHRENHEIT)
            and unit_of_measure != units.temperature_unit
        ):
            prec = len(state) - state.index(".") - 1 if "." in state else 0
            temp = units.temperature(float(state), unit_of_measure)
            state = str(round(temp) if prec == 0 else round(temp, prec))
            attr[ATTR_UNIT_OF_MEASUREMENT] = units.temperature_unit
    except ValueError:
        # Could not convert state to float
        pass

    return attr
