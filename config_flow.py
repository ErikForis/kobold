from homeassistant import config_entries
import voluptuous as vol
from homeassistant.core import callback

from .const import DOMAIN

DATA_SCHEMA = vol.Schema(
    {
        vol.Required("authKey"): str,
        # vol.Optional("update_interval", default=30): int,
    }
)


class KoboldConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    MINOR_VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            # Validate or test connection here if needed
            return self.async_create_entry(title="kobold", data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )
