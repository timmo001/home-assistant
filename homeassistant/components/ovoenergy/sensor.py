"""
Support for OVO Energy

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.ovo/
"""
# import asyncio
from datetime import datetime, timedelta
# from functools import partial
import logging

import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (CONF_NAME, CONF_USERNAME, CONF_PASSWORD)
# from homeassistant.core import CoreState
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity

_LOGGER = logging.getLogger(__name__)

REQUIREMENTS = ['ovoenergy==0.1.3']

ICON_GAS = 'mdi:fire'
ICON_POWER = 'mdi:flash'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_USERNAME): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
    vol.Optional(CONF_NAME, default="OVOEnergy"): cv.string
})


async def async_setup_platform(hass, config, async_add_entities,
                               discovery_info=None):
    """Set up the OVOEnergy sensor."""
    name = config.get('name')
    username = config.get('username')
    password = config.get('password')
    async_add_entities([
        OVOEntity('{} {}'.format(name, 'Electricity'),
                  username, password),  # Electricity
        OVOEntity('{} {}'.format(name, 'Gas'), username, password, True)  # Gas
    ])


class OVOEntity(Entity):
    """Entity reading values from DSMR telegram."""

    def __init__(self, name, username, password, gas=False):
        """Initialize entity."""
        from ovoenergy.ovoenergy import OVOEnergy
        self._name = name
        self._ovo = OVOEnergy(username, password)
        self._unit_of_measurement = 'kwh'
        self._gas = gas

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def icon(self):
        """Return icon to use in the frontend."""
        icon = ICON_POWER
        if self._gas is True:
            icon = ICON_GAS
        return icon

    @property
    def state(self):
        """Return the state of sensor."""
        value = None

        date = datetime.now()
        half_hourly_usage = self._ovo.get_half_hourly_usage(
            date.date().isoformat())

        # Due to the 'live' data from OVO being limited,
        # this should make sure there is always a value above 0
        list_id = -1
        while value is None or value <= 0:
            if self._gas is True:
                # If we reach the start of the list, try the previous days data
                if list_id * -1 >= len(half_hourly_usage['gas']):
                    list_id = -1
                    date = date - timedelta(days=1)
                    half_hourly_usage = self._ovo.get_half_hourly_usage(
                        date.date().isoformat())
                self._unit_of_measurement = half_hourly_usage['gas'][list_id]['unit']
                value = half_hourly_usage['gas'][list_id]['consumption']
            else:
                # If we reach the start of the list, try the previous days data
                if list_id * -1 >= len(half_hourly_usage['electricity']):
                    list_id = -1
                    date = date - timedelta(days=1)
                    half_hourly_usage = self._ovo.get_half_hourly_usage(
                        date.date().isoformat())
                self._unit_of_measurement = half_hourly_usage['electricity'][list_id]['unit']
                value = half_hourly_usage['electricity'][list_id]['consumption']
            list_id -= 1

        return value

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._unit_of_measurement
