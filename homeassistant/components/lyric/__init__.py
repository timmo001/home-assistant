"""Support for Honeywell Lyric devices."""
import asyncio
import logging
from typing import Any, Dict

from lyric import Lyric
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_CLIENT_ID, CONF_CLIENT_SECRET
from homeassistant.helpers import (
    aiohttp_client,
    config_entry_oauth2_flow,
    config_validation as cv,
)
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.typing import ConfigType, HomeAssistantType

from . import api, config_flow
from .const import DOMAIN, OAUTH2_AUTHORIZE, OAUTH2_TOKEN  # SERVICE_HOLD_TIME,

_LOGGER = logging.getLogger(__name__)

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

PLATFORMS = ["climate", "sensor"]


async def async_setup(hass: HomeAssistantType, config: ConfigType) -> bool:
    """Set up the Lyric component."""
    hass.data[DOMAIN] = {}

    if DOMAIN not in config:
        return True

    config_flow.OAuth2FlowHandler.async_register_implementation(
        hass,
        config_entry_oauth2_flow.LocalOAuth2Implementation(
            hass,
            DOMAIN,
            config[DOMAIN][CONF_CLIENT_ID],
            config[DOMAIN][CONF_CLIENT_SECRET],
            OAUTH2_AUTHORIZE,
            OAUTH2_TOKEN,
        ),
    )

    return True


async def async_setup_entry(hass: HomeAssistantType, entry: ConfigEntry) -> bool:
    """Set up Lyric from a config entry."""
    implementation = await config_entry_oauth2_flow.async_get_config_entry_implementation(
        hass, entry
    )

    session = config_entry_oauth2_flow.OAuth2Session(hass, entry, implementation)

    hass.data[DOMAIN][entry.entry_id] = api.AsyncConfigEntryAuth(
        aiohttp_client.async_get_clientsession(hass), session
    )

    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )

    return True

    # instance_key = f"{DOMAIN}_{entry.data[CONF_NAME]}"

    # lyric = Lyric(
    #     app_name="Home Assistant",
    #     client_id=entry.data[CONF_CLIENT_ID],
    #     client_secret=entry.data[CONF_CLIENT_SECRET],
    #     token=entry.data[CONF_TOKEN],
    #     token_cache_file=hass.config.path(CONF_LYRIC_CONFIG_FILE),
    # )

    # hass.data.setdefault(instance_key, {})[DATA_LYRIC_CLIENT] = LyricClient(lyric)

    # for component in PLATFORMS:
    #     hass.async_create_task(
    #         hass.config_entries.async_forward_entry_setup(entry, component)
    #     )

    # return True


async def async_unload_entry(hass: HomeAssistantType, entry: ConfigType) -> bool:
    """Unload Lyric config entry."""
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

    # instance_key = f"{DOMAIN}_{entry.data[CONF_NAME]}"

    # for component in "climate", "sensor":
    #     await hass.config_entries.async_forward_entry_unload(entry, component)

    # # Remove the climate service
    # hass.services.async_remove(instance_key, SERVICE_HOLD_TIME)

    # del hass.data[instance_key]

    # return True


class LyricClient:
    """Structure Lyric functions for hass."""

    def __init__(self, lyric: Lyric):
        """Init Lyric devices."""
        self._lyric = lyric

    def devices(self):
        """Generate a list of thermostats and their location."""
        for location in self._lyric.locations:
            for device in location.thermostats:
                yield (location, device)


class LyricEntity(Entity):
    """Defines a base Lyric entity."""

    def __init__(
        self, device, location, unique_id: str, name: str, icon: str, device_class: str
    ) -> None:
        """Initialize the Lyric entity."""
        self._unique_id = unique_id
        self._name = name
        self._icon = icon
        self._device_class = device_class
        self._available = False
        self.device = device
        self.location = location

    @property
    def unique_id(self) -> str:
        """Return unique ID for the sensor."""
        return self._unique_id

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return self._name

    @property
    def icon(self) -> str:
        """Return the mdi icon of the entity."""
        return self._icon

    @property
    def device_class(self) -> str:
        """Return the class of this device."""
        return self._device_class

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._available

    async def async_update(self) -> None:
        """Update Lyric entity."""
        await self._lyric_update()
        self._available = True

    async def _lyric_update(self) -> None:
        """Update Lyric entity."""
        raise NotImplementedError()


class LyricDeviceEntity(LyricEntity):
    """Defines a Lyric device entity."""

    @property
    def device_info(self) -> Dict[str, Any]:
        """Return device information about this Lyric instance."""
        mac_address = self.device.macID
        return {
            "identifiers": {(DOMAIN, mac_address)},
            "name": self.device.name,
            "model": self.device.id,
            "manufacturer": "Honeywell",
        }
