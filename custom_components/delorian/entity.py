import logging

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import UnitOfEnergy
from homeassistant.helpers.update_coordinator import CoordinatorEntity

LOGGER = logging.getLogger(__name__)


class DeloreanEntity(CoordinatorEntity):
    """The IDeSensor class provides:
    __init__
    __repr__
    name
    unique_id
    device_info
    entity_registry_enabled_default
    """

    def __init__(self, *args, name, entity_id, device_info, **kwargs):
        super().__init__(*args, **kwargs)

        self._attr_has_entity_name = True
        self._attr_name = name

        self._attr_entity_id = entity_id
        self._attr_unique_id = entity_id.replace(".", "-")

        self._attr_device_info = device_info
        self._attr_entity_registry_enabled_default = True
        self._attr_entity_registry_visible_default = True

        self._attr_state = None

        # Define whatever you are
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_device_class = SensorDeviceClass.ENERGY

        # We DON'T opt-in for statistics (don't set state_class). Why?
        #
        # Those statistics are generated from a real sensor, this sensor, but we don't
        # want that hass try to do anything with those statistics because we
        # (HistoricalSensor) handle generation and importing
        #
        # self._attr_state_class = SensorStateClass.MEASUREMENT

    async def async_added_to_hass(self) -> None:
        LOGGER.debug(f"{self.entity_id}: added to hass")

        await super().async_added_to_hass()
        await self.coordinator.async_request_refresh()

    async def async_will_remove_from_hass(self) -> None:
        LOGGER.debug(f"{self.entity_id}: will remove from hass")

        await super().async_will_remove_from_hass()
