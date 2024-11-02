import logging

logger = logging.getLogger(__name__)
from typing import Optional
from enum import IntEnum
import numpy as np
from . import Device
from hush.interfaces import http


class Rp2040(Device):
    def __init__(self, host: str) -> None:
        super().__init__(host)
        self.get_oob_credentials()

    async def close(self):
        await self.json_request.post(path="api/fanmode", payload={"use_ext_fan_ctrl": False})

    async def get_temp(self):
        response = await self.json_request.get(path="api/temperatures")
        self._temp = max(response.values())
        return self._temp

    async def set_speed(self, speed):
        self._speed = speed
        await self.json_request.post(path="api/fans", payload={"fan0": speed})

    @property
    def json_request(self) -> http.Json:
        if self._json_request is None:
            self._json_request = http.Json(self.hostname, self.username, self.password, secure=False)
        return self._json_request
