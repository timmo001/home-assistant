"""Config flow for Honeywell Lyric."""
import asyncio
import logging

from aiohttp import web_response
import async_timeout
from lyric import Lyric
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.http import HomeAssistantView
from homeassistant.components.lyric.const import (
    AUTH_CALLBACK_NAME,
    AUTH_CALLBACK_PATH,
    CONF_LYRIC_CONFIG_FILE,
    DOMAIN,
)
from homeassistant.config_entries import ConfigFlow
from homeassistant.const import (
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_NAME,
    CONF_TOKEN,
)

_LOGGER = logging.getLogger(__name__)


@config_entries.HANDLERS.register(DOMAIN)
class LyricFlowHandler(ConfigFlow, domain=DOMAIN):
    """Handle a Lyric config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def __init__(self):
        """Initialize Lyric flow."""
        self.lyric = None
        self.client_id = None
        self.client_secret = None
        self.name = None
        self.code = None

    async def _show_setup_form(self, errors=None):
        """Show the setup form to the user."""
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_CLIENT_ID): str,
                    vol.Required(CONF_CLIENT_SECRET): str,
                    vol.Optional(CONF_NAME, default="Lyric"): str,
                }
            ),
            errors=errors or {},
        )

    async def async_step_user(self, user_input=None, code=None):
        """Handle a flow initiated by the user."""
        if user_input is None:
            return await self._show_setup_form(user_input)

        self.client_id = user_input[CONF_CLIENT_ID]
        self.client_secret = user_input[CONF_CLIENT_SECRET]
        self.name = (
            user_input[CONF_NAME] if user_input[CONF_NAME] is not None else "Lyric"
        )

        return await self.async_step_auth(code)

    async def async_step_auth(self, code=None):
        """Create an entry for auth."""
        # Flow has been triggered from Lyric api
        if code is not None:
            return await self.async_step_code(code)

        try:
            with async_timeout.timeout(10):
                client_id = self.client_id
                client_secret = self.client_secret
                redirect_uri = "{}{}".format(
                    self.hass.config.api.base_url, AUTH_CALLBACK_PATH
                )
                token_cache_file = self.hass.config.path(CONF_LYRIC_CONFIG_FILE)

                self.lyric = Lyric(
                    app_name="Home Assistant",
                    client_id=client_id,
                    client_secret=client_secret,
                    redirect_uri=redirect_uri,
                    token_cache_file=token_cache_file,
                )

                self.hass.http.register_view(LyricAuthCallbackView())

                url = self.lyric.getauthorize_url

                return self.async_external_step(
                    step_id="auth", url=url[: url.find("&state=") + 7] + self.flow_id
                )
        except asyncio.TimeoutError:
            return self.async_abort(reason="authorize_url_timeout")

    async def async_step_code(self, code):
        """Received code for authentication."""
        self.code = code
        return self.async_external_step_done(next_step_id="creation")

    async def async_step_creation(self, user_input=None):
        """Create Lyric api and entries."""
        self.lyric.authorization_code(self.code, self.flow_id)

        return self.async_create_entry(
            title=self.name,
            data={
                CONF_NAME: self.name,
                CONF_CLIENT_ID: self.client_id,
                CONF_CLIENT_SECRET: self.client_secret,
                CONF_TOKEN: self.lyric.token,
            },
        )


class LyricAuthCallbackView(HomeAssistantView):
    """Lyric Authorization Callback View."""

    requires_auth = False
    name = AUTH_CALLBACK_NAME
    url = AUTH_CALLBACK_PATH

    async def get(self, request):
        """Receive authorization code."""

        if "code" not in request.query or "state" not in request.query:
            return web_response.Response(
                text=f"Missing code or state parameter in {request.url}"
            )

        hass = request.app["hass"]
        hass.async_create_task(
            hass.config_entries.flow.async_configure(
                flow_id=request.query["state"], user_input=request.query["code"]
            )
        )

        return web_response.Response(
            headers={"content-type": "text/html"},
            text="<script>window.close()</script>",
        )
