"""The Honeywell Lyric integration."""
import asyncio
from datetime import timedelta
import logging
from typing import Any, Dict

from aiolyric import Lyric
from aiolyric.objects.device import LyricDevice
from aiolyric.objects.location import LyricLocation
import async_timeout
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_CLIENT_ID, CONF_CLIENT_SECRET
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import (
    aiohttp_client,
    config_entry_oauth2_flow,
    config_validation as cv,
)
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import ConfigEntryLyricClient, LyricLocalOAuth2Implementation
from .config_flow import OAuth2FlowHandler
from .const import DOMAIN, LYRIC_EXCEPTIONS, OAUTH2_AUTHORIZE, OAUTH2_TOKEN

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_CLIENT_ID): cv.string,
                vol.Required(CONF_CLIENT_SECRET): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["climate"]


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Honeywell Lyric component."""
    hass.data[DOMAIN] = {}

    if DOMAIN not in config:
        return True

    hass.data[DOMAIN][CONF_CLIENT_ID] = config[DOMAIN][CONF_CLIENT_ID]

    OAuth2FlowHandler.async_register_implementation(
        hass,
        LyricLocalOAuth2Implementation(
            hass,
            DOMAIN,
            config[DOMAIN][CONF_CLIENT_ID],
            config[DOMAIN][CONF_CLIENT_SECRET],
            OAUTH2_AUTHORIZE,
            OAUTH2_TOKEN,
        ),
    )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Honeywell Lyric from a config entry."""
    implementation = (
        await config_entry_oauth2_flow.async_get_config_entry_implementation(
            hass, entry
        )
    )

    session = aiohttp_client.async_get_clientsession(hass)
    oauth_session = config_entry_oauth2_flow.OAuth2Session(hass, entry, implementation)

    client = ConfigEntryLyricClient(session, oauth_session)

    client_id = hass.data[DOMAIN][CONF_CLIENT_ID]
    lyric: Lyric = Lyric(client, client_id)

    try:
        await lyric.get_locations()
    except LYRIC_EXCEPTIONS as exception:
        _LOGGER.warning(exception)
        raise ConfigEntryNotReady from exception

    async def async_update_data() -> Lyric:
        """Fetch data from Lyric."""
        async with async_timeout.timeout(60):
            try:
                await lyric.get_locations()
            except LYRIC_EXCEPTIONS as exception:
                raise UpdateFailed(exception) from exception
            return lyric

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        # Name of the data. For logging purposes.
        name="lyric_coordinator",
        update_method=async_update_data,
        # Polling interval. Will only be polled if there are subscribers.
        update_interval=timedelta(seconds=120),
    )

    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Fetch initial data so we have data when entities subscribe
    await coordinator.async_refresh()

    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in PLATFORMS
            ]
        )
    )
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class LyricEntity(CoordinatorEntity):
    """Defines a base Honeywell Lyric entity."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        location: LyricLocation,
        device: LyricDevice,
        key: str,
        name: str,
        icon: str,
    ) -> None:
        """Initialize the Honeywell Lyric entity."""
        super().__init__(coordinator)
        self._update_thermostat = coordinator.data.update_thermostat
        self._device = device
        self._location = location
        self._key = key
        self._name = name
        self._icon = icon
        self._available = True

    @property
    def unique_id(self) -> str:
        """Return the unique ID for this entity."""
        return self._key

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return self._name

    @property
    def icon(self) -> str:
        """Return the mdi icon of the entity."""
        return self._icon

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success and self._available


class LyricDeviceEntity(LyricEntity):
    """Defines a Honeywell Lyric device entity."""

    @property
    def device_info(self) -> Dict[str, Any]:
        """Return device information about this Honeywell Lyric instance."""
        return {
            "identifiers": {(DOMAIN, self._device.macID)},
            "manufacturer": "Honeywell",
            "model": self._device.deviceModel,
            "name": self._device.name,
        }