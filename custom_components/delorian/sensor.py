# -*- coding: utf-8 -*-

# Copyright (C) 2021-2022 Luis López <luis@cuarentaydos.com>
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


# TODO
# Maybe we need to mark some function as callback but I'm not sure whose.
# from homeassistant.core import callback


# Check sensor.SensorEntityDescription
# https://github.com/home-assistant/core/blob/dev/homeassistant/components/sensor/__init__.py


from typing import Optional

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ENERGY_KILO_WATT_HOUR
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import DiscoveryInfoType
from homeassistant_historical_sensor import (
    DatedState,
    HistoricalSensor,
    PollUpdateMixin,
)

from .api import API
from .const import DOMAIN, NAME

PLATFORM = "sensor"


class Sensor(PollUpdateMixin, HistoricalSensor, SensorEntity):
    def __init__(self, *args, **kwargs):
        self._attr_has_entity_name = True
        self._attr_name = NAME

        self._attr_unique_id = NAME
        self._attr_entity_id = NAME

        self._attr_entity_registry_enabled_default = True
        self._attr_state = None

        # Simulate energy consumption source
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_native_unit_of_measurement = ENERGY_KILO_WATT_HOUR

        # Without state-class attr HomeAssistant will not show this sensor as
        # source for energy stats leaving generated statistics as the only
        # source.

        # self._attr_state_class = SensorStateClass.MEASUREMENT

        self.api = API()

    async def async_update_historical(self):
        self._attr_historical_states = [
            DatedState(
                state=state,
                when=dt,
            )
            for dt, state in self.api.fetch()
        ]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_devices: AddEntitiesCallback,
    discovery_info: Optional[DiscoveryInfoType] = None,  # noqa DiscoveryInfoType | None
):
    device_info = hass.data[DOMAIN][config_entry.entry_id]
    sensors = [
        Sensor(config_entry=config_entry, device_info=device_info),
    ]
    async_add_devices(sensors)
