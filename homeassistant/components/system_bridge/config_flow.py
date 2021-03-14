"""Config flow for System Bridge integration."""
import logging
from typing import Any, Dict, Optional

import async_timeout
from systembridge import Bridge
from systembridge.client import BridgeClient
from systembridge.exceptions import BridgeAuthenticationException
from systembridge.objects.network import Interface, Network
from systembridge.objects.os import Os
import voluptuous as vol

from homeassistant import config_entries, core, exceptions
from homeassistant.const import CONF_API_KEY, CONF_HOST, CONF_PORT
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers.typing import DiscoveryInfoType

from .const import BRIDGE_CONNECTION_ERRORS, DOMAIN  # pylint:disable=unused-import

_LOGGER = logging.getLogger(__name__)

# TODO adjust the data schema to the data that you need
STEP_AUTHENTICATE_DATA_SCHEMA = vol.Schema({vol.Required(CONF_API_KEY): str})
STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=9170): int,
        vol.Required(CONF_API_KEY): str,
    }
)


async def validate_input(hass: core.HomeAssistant, data):
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    if data.get(CONF_HOST, None) is None:
        raise InvalidHost
    if data.get(CONF_PORT, None) is None:
        raise InvalidHost
    if data.get(CONF_API_KEY, None) is None:
        raise InvalidAuth

    bridge = Bridge(
        BridgeClient(aiohttp_client.async_get_clientsession(hass)),
        f"http://{data[CONF_HOST]}:{data[CONF_PORT]}",
        data[CONF_API_KEY],
    )

    hostname = data[CONF_HOST]
    try:
        async with async_timeout.timeout(10):
            os: Os = await bridge.async_get_os()
            network: Network = await bridge.async_get_network()
            if os.hostname is not None:
                hostname = os.hostname
            interface: Interface = network.interfaces[network.interfaceDefault]
    except BridgeAuthenticationException:
        raise InvalidAuth
    except BRIDGE_CONNECTION_ERRORS:
        raise CannotConnect

    return {"hostname": hostname, "mac": interface["mac"]}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for System Bridge."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def __init__(self):
        """Initialize flow."""
        self._name: Optional[str] = None
        self._input: Optional[Dict[str, Any]] = None

    async def _async_get_info(self, user_input=None):
        errors = {}

        try:
            info = await validate_input(self.hass, user_input)
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except InvalidAuth:
            errors["base"] = "invalid_auth"
        except InvalidHost:
            errors["base"] = "invalid_host"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            return None, info

        return errors, None

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if self._input is not None:
            if user_input is not None:
                user_input = {**self._input, **user_input}
            else:
                user_input = self._input
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors, info = await self._async_get_info(user_input)
        if errors is None:
            # Check if already configured
            await self.async_set_unique_id(info["mac"])
            self._abort_if_unique_id_configured(updates={CONF_HOST: info["hostname"]})

            return self.async_create_entry(title=info["hostname"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_authenticate(self, user_input=None):
        """Handle getting the api-key for authentication."""
        if self._input is not None:
            if user_input is not None:
                user_input = {**self._input, **user_input}
            else:
                user_input = self._input
        if user_input is None or user_input.get(CONF_API_KEY, None) is None:
            return self.async_show_form(
                step_id="authenticate",
                data_schema=STEP_AUTHENTICATE_DATA_SCHEMA,
                description_placeholders={"name": self._name},
            )

        errors, info = await self._async_get_info(user_input)
        if errors is None:
            # Check if already configured
            await self.async_set_unique_id(info["mac"])
            self._abort_if_unique_id_configured(updates={CONF_HOST: info["hostname"]})

            return self.async_create_entry(title=info["hostname"], data=user_input)
        elif errors["base"] == "cannot_connect" or errors["base"] == "invalid_host":
            return await self.async_step_user(user_input)

        return self.async_show_form(
            step_id="authenticate",
            data_schema=STEP_AUTHENTICATE_DATA_SCHEMA,
            description_placeholders={"name": self._name},
            errors=errors,
        )

    async def async_step_zeroconf(self, discovery_info: DiscoveryInfoType):
        """Handle zeroconf discovery."""
        fqdn = discovery_info["properties"].get("fqdn", None)
        host = (
            fqdn
            if fqdn is not None
            else discovery_info["properties"].get("host", discovery_info[CONF_HOST])
        )
        mac = discovery_info["properties"].get("mac", None)

        # Check if already configured
        await self.async_set_unique_id(mac)
        self._abort_if_unique_id_configured(updates={CONF_HOST: host})

        self._name = host
        self._input = {
            CONF_HOST: host,
            CONF_PORT: discovery_info["properties"].get("port", None),
        }

        return await self.async_step_authenticate(self._input)


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(exceptions.HomeAssistantError):
    """Error to indicate there is invalid auth."""


class InvalidHost(exceptions.HomeAssistantError):
    """Error to indicate there is an invalid host."""
