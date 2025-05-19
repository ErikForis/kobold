from homeassistant.core import HomeAssistant

import logging

DOMAIN = "kobold"

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict):
    return True


async def async_setup_entry(hass, entry):
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setups(entry, ["button"])
    )
    return True
