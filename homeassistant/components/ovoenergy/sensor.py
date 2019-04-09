"""
Support for OVO Energy

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.ovo/
"""
# import asyncio
from datetime import datetime
# from functools import partial
import logging

import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (CONF_NAME, CONF_USERNAME, CONF_PASSWORD)
# from homeassistant.core import CoreState
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity

_LOGGER = logging.getLogger(__name__)

REQUIREMENTS = ['ovoenergy==0.1.0']

ICON_GAS = 'mdi:fire'
ICON_POWER = 'mdi:flash'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_USERNAME): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
    vol.Optional(CONF_NAME, default="OVO"): cv.string
})


async def async_setup_platform(hass, config, async_add_entities):
    """Set up the OVOEnergy sensor."""
    entity = OVOEntity(config.get('name'),
                       config.get('username'),
                       config.get('password'))

    async_add_entities([entity])


class OVOEntity(Entity):
    """Entity reading values from DSMR telegram."""

    def __init__(self, name, username, password):
        """Initialize entity."""
        from ovoenergy.ovoenergy import OVOEnergy
        self._name = name
        self._ovo = OVOEnergy(username, password)
        self._daily_usage = None
        self._half_hourly_usage = None

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def icon(self):
        """Return icon to use in the frontend."""
        if 'Power' in self._name:
            return ICON_POWER
        if 'Gas' in self._name:
            return ICON_GAS

    @property
    def state(self):
        """Return the state of sensor."""
        date = datetime.now().date().isoformat()
        _LOGGER.debug(date)
        _LOGGER.debug(date[-3])

        self._daily_usage = self._ovo.get_daily_usage(date[-3])
        self._half_hourly_usage = self._ovo.get_half_hourly_usage(date)

        value = 'test'

        return value

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return 'kWh'
