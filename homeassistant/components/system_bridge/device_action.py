"""Provides device actions for System Bridge."""
from typing import List, Optional

import voluptuous as vol

from homeassistant.const import (
    ATTR_DEVICE_ID,
    CONF_DEVICE_ID,
    CONF_DOMAIN,
    CONF_ENTITY_ID,
    CONF_TYPE,
)
from homeassistant.core import Context, HomeAssistant
import homeassistant.helpers.config_validation as cv

from . import (
    DOMAIN,
    SERVICE_OPEN,
    SERVICE_OPEN_SCHEMA,
    SERVICE_SEND_COMMAND,
    SERVICE_SEND_COMMAND_SCHEMA,
)

ACTION_TYPES = {SERVICE_SEND_COMMAND, SERVICE_OPEN}

SEND_COMMAND_ACTION_SCHEMA = cv.DEVICE_ACTION_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_TYPE): vol.In(ACTION_TYPES),
        vol.Required(CONF_ENTITY_ID): cv.entity_domain(DOMAIN),
        **SERVICE_SEND_COMMAND_SCHEMA,
    }
)

OPEN_ACTION_SCHEMA = cv.DEVICE_ACTION_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_TYPE): vol.In(ACTION_TYPES),
        vol.Required(CONF_ENTITY_ID): cv.entity_domain(DOMAIN),
        **SERVICE_OPEN_SCHEMA,
    }
)

ACTION_SCHEMA = vol.Any(SEND_COMMAND_ACTION_SCHEMA, OPEN_ACTION_SCHEMA)


async def async_get_actions(hass: HomeAssistant, device_id: str) -> List[dict]:
    """List device actions for System Bridge devices."""
    # device_registry = await hass.helpers.device_registry.async_get_registry()
    # device_entry = device_registry.async_get(device_id)

    actions = [
        {
            CONF_DEVICE_ID: device_id,
            CONF_DOMAIN: DOMAIN,
            CONF_TYPE: SERVICE_SEND_COMMAND,
        },
        {
            CONF_DEVICE_ID: device_id,
            CONF_DOMAIN: DOMAIN,
            CONF_TYPE: SERVICE_OPEN,
        },
    ]

    return actions


async def async_call_action_from_config(
    hass: HomeAssistant, config: dict, variables: dict, context: Optional[Context]
) -> None:
    """Execute a device action."""
    print(config)
    print(variables)
    print(context)
    service_data = {ATTR_DEVICE_ID: config[CONF_DEVICE_ID]}

    if config[CONF_TYPE] == SERVICE_SEND_COMMAND:
        service = SERVICE_SEND_COMMAND
    elif config[CONF_TYPE] == SERVICE_OPEN:
        service = SERVICE_OPEN

    await hass.services.async_call(
        DOMAIN, service, service_data, blocking=True, context=context
    )
