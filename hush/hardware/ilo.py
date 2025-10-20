import logging

logger = logging.getLogger(__name__)
from typing import Any, Dict, List, Optional
import time
import re
import numpy as np
from . import Device
from hush.interfaces import ssh


class iLO4(Device):
    thermal_info: Dict[str, Dict[str, Any]] = {}

    def __init__(self, host: str, fans: Optional[List[str]] = None, temps: List[str] = []) -> None:
        super().__init__(host)
        self._fans = fans
        self._temps = temps
        self.get_oob_credentials()
        self.json_request.base_path = f"https://{self.hostname}/redfish/v1/"

    async def close(self):
        if self._fans is not None and len(self._fans) > 0:
            for fan in self._fans:
                f = int(fan[4:]) - 1
                await self.ssh.shell(f"fan p {f} unlock")

    async def get_thermal_info(self, cache_lifetime=60):
        if self.hostname not in self.thermal_info:
            self.thermal_info[self.hostname] = {"data": {}, "timestamp": 0}
        if time.time() - self.thermal_info[self.hostname]["timestamp"] > cache_lifetime:
            self.thermal_info[self.hostname]["data"] = await self.json_request.get("chassis/1/Thermal/")
            self.thermal_info[self.hostname]["timestamp"] = time.time()
        return self.thermal_info[self.hostname]["data"]

    async def get_fan_names(self):
        response = await self.get_thermal_info()
        fans = []
        for fan in response["Fans"]:
            if fan["Status"]["State"] == "Enabled":
                fans.append(fan["FanName"])
        return fans

    async def _get_temp_names(self, filters: List[str]):
        response = await self.get_thermal_info()
        temps = []
        for temp in response["Temperatures"]:
            for filter in filters:
                if filter in temp["Name"] and temp["Status"]["State"] == "Enabled":
                    temps.append(temp["Name"][3:])
        return temps

    async def get_cpu_temp_names(self):
        return await self._get_temp_names(filters=["CPU"])

    async def set_cpu_temp_names(self):
        self._temps = await self.get_cpu_temp_names()

    async def get_pci_temp_names(self):
        return await self._get_temp_names(filters=["PCI", "HD", "LOM"])

    async def set_pci_temp_names(self):
        self._temps = await self.get_pci_temp_names()

    async def get_temp(self):
        temps = []
        response = await self.get_thermal_info(cache_lifetime=3)
        for temperature in response["Temperatures"]:
            for t in self._temps:
                if t == temperature["Name"][3:] and temperature["Status"]["State"] == "Enabled":
                    temps.append(float(temperature["CurrentReading"]))
        self._temp = int(np.max(temps))
        return self._temp

    async def set_speed(self, speed):
        self._speed = speed
        pwm = int((self._speed / 100) * 255)
        if self._fans == []:
            self._fans = await self.get_fan_names()
        for fan in self._fans:
            numbers = re.findall(r"\d+", fan)
            f = int(numbers) - 1
            await self.ssh.shell(f"fan p {f} lock {pwm}")

    @property
    def ssh(self) -> ssh.Ssh:
        if self._ssh is None:
            self.get_oob_credentials()
            self._ssh = ssh.Ssh(
                f"{self.host}_oob",
                password=self.password,
                options={
                    "PubKeyAcceptedKeyTypes": "+ssh-rsa",
                    "HostKeyAlgorithms": "+ssh-rsa",
                    "KexAlgorithms": "+diffie-hellman-group14-sha1",
                },
            )
        return self._ssh
