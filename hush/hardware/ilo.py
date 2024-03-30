import logging

logger = logging.getLogger(__name__)
from typing import Optional
import numpy as np
from . import Device
from hush.interfaces import ssh


class iLO4(Device):
    def __init__(self, host: str) -> None:
        super().__init__(host)
        self.get_oob_credentials()
        self.json_request.base_path = f"https://{self.hostname}/redfish/v1/"
        self._fan_count = None

    async def close(self):
        if self._fan_count is not None and self._fan_count > 0:
            for fan in range(self._fan_count):
                await self.ssh.shell(f"fan p {fan} unlock")

    async def get_fan_count(self):
        response = await self.json_request.get("chassis/1/Thermal")
        self._fan_count = len(response["Fans"])
        return self._fan_count

    async def get_temp(self, core=None):
        cpu_temps = list()
        response = await self.json_request.get("chassis/1/Thermal")
        for temperature in response["Temperatures"]:
            if temperature["Name"].find("CPU") != -1:
                cpu_temps.append(float(temperature["CurrentReading"]))
        if core is None:
            self._temp = int(np.mean(cpu_temps))
        else:
            self._temp = cpu_temps[core]
        return self._temp

    async def set_speed(self, speed):
        self._speed = speed
        if self._fan_count is None:
            await self.get_fan_count()
        pwm = int((self._speed / 100) * 255)
        for fan in range(self._fan_count):
            await self.ssh.shell(f"fan p {fan} lock {pwm}")

    @property
    def ssh(self) -> ssh.Ssh:
        if self._ssh is None:
            self.get_oob_credentials()
            self._ssh = ssh.Ssh(
                f"{self.host}_oob",
                password=self.password,
                options={
                    "PubKeyAcceptedKeyTypes": "+ssh-rsa",
                    "HostKeyAlgorithms": "+ssh-dss",
                    "KexAlgorithms": "+diffie-hellman-group14-sha1",
                },
            )
        return self._ssh
