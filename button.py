from datetime import UTC, datetime
import hmac
import json
import logging

import curl_cffi

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    BEEHIVE_BASE_URL,
    BEEHIVE_MAP_BASE_URL,
    DASHBORD_PATH,
    DOMAIN,
    MASSAGES_PATH,
    NUKLIO_BASE_URL,
    PERSISTANT_MAP_PATH,
    TOKEN_TYPE,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    token = entry.data.get("authKey")
    res = curl_cffi.get(
        BEEHIVE_BASE_URL + DASHBORD_PATH,
        headers={
            "Authorization": TOKEN_TYPE + " " + token,
            "Accept": "application/vnd.neato.beehive.v1+json",
        },
    )

    res = json.loads(res.text)
    robotSerial = res["robots"][0]["serial"]
    robotSecretKey = res["robots"][0]["secret_key"]
    hass.data[DOMAIN] = {
        "robot_serial": robotSerial,
        "robot_secret_key": robotSecretKey,
    }
    _LOGGER.debug(hass.data[DOMAIN]["robot_serial"])

    url = BEEHIVE_MAP_BASE_URL + "/" + robotSerial + PERSISTANT_MAP_PATH
    res = curl_cffi.get(
        url=url,
        impersonate="firefox",
        verify=False,
        headers={
            "Authorization": TOKEN_TYPE + " " + token,
            "Accept": "application/vnd.neato.beehive.v1+json",
        },
    )
    res = json.loads(res.text)
    maps = [{i["name"]: i["id"]} for i in res]
    for localmap in maps:
        async_add_entities(
            [CleanButton(hass, list(localmap.keys())[0], list(localmap.values())[0])]
        )
        data = {
            "reqId": 1,
            "cmd": "getMapBoundaries",
            "params": {"mapId": list(localmap.values())[0]},
        }
        headers = await MultiPurposeButton.gen_headers(
            robotSerial, robotSecretKey, data
        )
        res = curl_cffi.post(
            url=NUKLIO_BASE_URL + "/" + robotSerial + MASSAGES_PATH,
            impersonate="firefox",
            verify=False,
            headers=headers,
            data=json.dumps(data),
        )
        res = json.loads(res.text)
        for boundary in res["data"]["boundaries"]:
            if boundary["type"] == "polygon":
                async_add_entities(
                    [CleanButton(hass, boundary["name"], boundary["id"])]
                )

    _LOGGER.debug("got maps")

    async_add_entities(
        [
            MultiPurposeButton(hass, "FindME", "findMe", None),
            MultiPurposeButton(
                hass,
                "StartCleaning",
                "startCleaning",
                {
                    "category": 2,
                    "mode": 1,
                    "modifier": 1,
                    "navigatioMode": "null",
                },
            ),
            MultiPurposeButton(hass, "GoToBase", "sendToBase", None),
        ]
    )


class MultiPurposeButton(ButtonEntity):
    def __init__(self, hass: HomeAssistant, name: str, cmd: str, params: str):
        if params:
            self.data = {"reqId": 77, "cmd": cmd, "params": params}
        else:
            self.data = {"reqId": 77, "cmd": cmd}

        self._key = hass.data[DOMAIN]["robot_secret_key"]
        self._serial = hass.data[DOMAIN]["robot_serial"]

        self._attr_name = name
        self.url = NUKLIO_BASE_URL + "/" + self._serial + MASSAGES_PATH
        self._attr_unique_id = DOMAIN + "_" + name

    async def gen_headers(serial, key, data: str) -> str:
        now = datetime.now(UTC)
        # format the date string
        formatted_date = now.strftime("%a, %d %b %Y %H:%M:%S GMT")
        _LOGGER.debug(data)
        # dataFormat = (
        #    '{"reqId":' + str(data["reqId"]) + ',"cmd":' + '"' + data["cmd"] + '"' + "}"
        # )
        dataFormat = json.dumps(data)
        sign = serial.lower() + "\n" + formatted_date + "\n" + dataFormat
        signature = hmac.new(
            key.encode(), sign.encode(), digestmod="sha256"
        ).hexdigest()

        return {
            "accept": "application/vnd.neato.nucleo.v1",
            "date": formatted_date,
            "authorization": "NEATOAPP " + str(signature),
        }

    async def async_press(self) -> None:
        headers = await MultiPurposeButton.gen_headers(
            self._serial, self._key, self.data
        )
        dataFormat = json.dumps(self.data)
        result = curl_cffi.post(
            url=self.url,
            impersonate="firefox",
            verify=False,
            headers=headers,
            data=dataFormat,
        )
        _LOGGER.debug(result.text)


class CleanButton(MultiPurposeButton):
    def __init__(self, hass: HomeAssistant, name, boundryID):
        params = {
            "category": 4,
            "mode": 1,
            "navigationMode": 1,
            "boundaryId": boundryID,
        }
        super().__init__(hass, name, "startCleaning", params=params)
