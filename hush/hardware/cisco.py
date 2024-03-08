import logging

logger = logging.getLogger(__name__)
from typing import Optional, Union
import numpy as np
from enum import IntEnum
from datetime import datetime as dt
import time
from . import Device


# https://www.cisco.com/c/en/us/td/docs/unified_computing/ucs/c/sw/api/4_3/b-cisco-imc-xml-api-43.pdf


class M3(Device):
    class FanPolicy(IntEnum):
        LOWPOWER = 0
        BALANCED = 1
        PERFORMANCE = 2
        HIGHPOWER = 3
        MAXIMUMPOWER = 4

    def __init__(self, host: str) -> None:
        super().__init__(host)
        self.get_oob_credentials()
        self.xml_request.base_path = f"https://{self.hostname}/nuova"
        self._cookie = ""
        self._cookie_time = dt.now()
        self._cookie_timeout = 0

    async def close(self) -> None:
        cookie = await self.cookie()
        await self.xml_request.post(f"<aaaLogout inCookie='{cookie}'></aaaLogout>")

    async def set_speed(self, speed: Union[str, int, FanPolicy]) -> None:
        self._speed = speed
        if isinstance(speed, str):
            policy_map = {
                "Low Power": self.FanPolicy.LOWPOWER,
                "Balanced": self.FanPolicy.BALANCED,
                "Performance": self.FanPolicy.PERFORMANCE,
                "High Power": self.FanPolicy.HIGHPOWER,
                "Max Power": self.FanPolicy.MAXIMUMPOWER,
            }
            policy = policy_map[speed]
        elif isinstance(speed, M3.FanPolicy):
            policy = speed
        elif isinstance(speed, int):
            if speed < 25:
                policy = self.FanPolicy.LOWPOWER
            elif speed < 50:
                policy = self.FanPolicy.BALANCED
            elif speed < 75:
                policy = self.FanPolicy.PERFORMANCE
            elif speed < 100:
                policy = self.FanPolicy.HIGHPOWER
            else:
                policy = self.FanPolicy.MAXIMUMPOWER
        else:
            policy = speed
        policys = {
            self.FanPolicy.LOWPOWER: "Low Power",
            self.FanPolicy.BALANCED: "Balanced",
            self.FanPolicy.PERFORMANCE: "Performance",
            self.FanPolicy.HIGHPOWER: "High Power",
            self.FanPolicy.MAXIMUMPOWER: "Maximum Power",
        }
        cookie = await self.cookie()
        data = f"<configConfMo cookie='{cookie}' inHierarchical='false' dn='sys/rack-unit-1/board/fan-policy'><inConfig><fanPolicy configuredFanPolicy='{policys[policy]}' dn='sys/rack-unit-1/board/fan-policy'></fanPolicy></inConfig></configConfMo>"
        try:
            response = await self.xml_request.post(data)
            status = response["configConfMo"]["@response"]
            if status != "yes":
                raise Exception
        except Exception as e:
            logger.error(f"{self.hostname} failed to set fan policy")
            logger.error(f"response = {response}")
            raise e

    async def get_temp(self, core: Optional[int] = None) -> int:
        try:
            cookie = await self.cookie()
            data = f"<configResolveClass cookie='{cookie}' inHierarchical='false' classId='processorEnvStats'></configResolveClass>"
            response = await self.xml_request.post(data)
            cpus = response["configResolveClass"]["outConfigs"]["processorEnvStats"]
            if not isinstance(cpus, list):
                cpus = [cpus]
            cpu_temps = []
            for cpu in cpus:
                cpu_temps.append(float(cpu["@temperature"]))
            if core is None:
                self._temp = int(np.mean(cpu_temps))
            else:
                self._temp = int(cpu_temps[core])
            return self._temp
        except Exception as e:
            logger.error(f"{self.hostname} failed to get cpu temp")
            logger.error(f"response = {response}")
            raise e

    async def cookie(self) -> str:
        try:
            elapsed_time = dt.now() - self._cookie_time
            if self._cookie == "" or elapsed_time.seconds > (self._cookie_timeout - 10):
                self._cookie_time = dt.now()
                data = f"<aaaLogin inName='{self.username}' inPassword='{self.password}'></aaaLogin>"
                response = await self.xml_request.post(data)
                self._cookie = response["aaaLogin"]["@outCookie"]
                self._cookie_timeout = int(response["aaaLogin"]["@outRefreshPeriod"])
            return self._cookie
        except Exception as e:
            logger.error(f"{self.hostname} failed to get cookie")
            logger.error(f"response = {response}")
            raise e
