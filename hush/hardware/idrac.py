import logging

logger = logging.getLogger(__name__)
from typing import Optional
from enum import IntEnum
import json
import re
import numpy as np
from . import Device

# https://www.dell.com/support/manuals/en-us/idrac9-lifecycle-controller-v6.x-series/idrac9_6.xx_racadm_pub/introduction
# https://dl.dell.com/content/manual35024470-integrated-dell-remote-access-controller-9-racadm-cli-guide.pdf?language=en-us
# https://www.dell.com/support/manuals/en-us/idrac9-lifecycle-controller-v6.x-series/idrac9_6.xx_racadm_ar_guide/notes-cautions-and-warnings
# https://dl.dell.com/content/manual36782628-integrated-dell-remote-access-controller-9-attribute-registry.pdf?language=en-us
# https://www.dell.com/support/manuals/en-us/idrac9-lifecycle-controller-v6.x-series/idrac9_6.xx_ug/notes-cautions-and-warnings
# https://dl.dell.com/content/manual38875502-integrated-dell-remote-access-controller-9-user-s-guide.pdf?language=en-us


class Redfish(Device):
    class Fan_Offset(IntEnum):
        OFF = 0
        LOW = 1
        MEDIUM = 2
        HIGH = 3
        MAX = 4

    def __init__(self, host: str) -> None:
        super().__init__(host)
        self.get_oob_credentials()
        self.json_request.base_path = f"https://{self.hostname}/redfish/v1/"

    async def get_temp(self, core=None):
        cpu_temps = list()
        response = None
        try:
            response = await self.json_request.get(path="Chassis/System.Embedded.1/Sensors")
            sensor_paths = re.findall(r"Chassis\/System.Embedded.1\/Sensors\/CPU\dTemp", str(response))
            for sensor_path in sensor_paths:
                response = await self.json_request.get(path=f"{sensor_path}")
                cpu_temps.append(float(response["Reading"]))
        except Exception as e:
            if response is not None:
                logger.error(f"{self.hostname} failed to get cpu temperature from: {response}")
            raise e
        if core is None:
            self._temp = int(np.max(cpu_temps))
        else:
            self._temp = cpu_temps[core]
        return self._temp

    async def set_speed(self, speed):
        response = None
        if isinstance(speed, str) is True:
            offsets = {
                "Off": self.Fan_Offset.OFF,
                "Low": self.Fan_Offset.LOW,
                "Medium": self.Fan_Offset.MEDIUM,
                "High": self.Fan_Offset.HIGH,
                "Max": self.Fan_Offset.MAX,
            }
            offset = offsets[speed]
        elif isinstance(speed, int) is True:
            if speed < 25:
                offset = self.Fan_Offset.OFF
            elif speed < 50:
                offset = self.Fan_Offset.LOW
            elif speed < 75:
                offset = self.Fan_Offset.MEDIUM
            elif speed < 100:
                offset = self.Fan_Offset.HIGH
            else:
                offset = self.Fan_Offset.MAX
        else:
            offset = speed
        offsets = {
            self.Fan_Offset.OFF: "Off",
            self.Fan_Offset.LOW: "Low",
            self.Fan_Offset.MEDIUM: "Medium",
            self.Fan_Offset.HIGH: "High",
            self.Fan_Offset.MAX: "Max",
        }
        if self._speed != offsets[offset]:
            self._speed = offsets[offset]
            response = await self.json_request.patch(
                path="Managers/System.Embedded.1/Attributes",
                payload={"Attributes": {"ThermalSettings.1.FanSpeedOffset": self._speed}},
            )
            output = json.dumps(response)
            try:
                output.index("The request completed successfully.")
                output.index("The operation successfully completed.")
            except Exception as e:
                if response is not None:
                    logger.error(f"{self.hostname} failed to get cpu temperature from: {response}")
                raise e


class Ipmi(Device):
    class FanMode(IntEnum):
        MANUAL = 0
        IDRAC = 1

    def __init__(self, host: str) -> None:
        super().__init__(host)
        self.get_oob_credentials()
        self._fan_mode = self.FanMode.IDRAC

    async def close(self) -> None:
        await self.set_fan_mode(self.FanMode.IDRAC)

    async def set_fan_mode(self, mode: FanMode) -> None:
        result = await self.ipmi.execute(f"raw 0x30 0x30 0x01 0x0{int(mode)}")
        if result.stdout != "\n":
            raise Exception
        else:
            self._fan_mode = mode

    async def get_temp(self, core=None):
        cpu_temps = list()
        response = None
        try:
            response = await self.ipmi.execute("-c sdr")
            data_lines = response.stdout_lines
            for data in data_lines:
                data = data.split(",")
                if data[0] == "Temp" and data[1] != "":
                    cpu_temps.append(float(data[1]))
            if core is None:
                self._temp = int(np.max(cpu_temps))
            else:
                self._temp = cpu_temps[core]
            return self._temp
        except Exception as e:
            if response is not None:
                logger.error(f"{self.hostname} failed to get cpu temperature from: {response}")
            raise e

    async def set_speed(self, speed: int) -> None:
        self._speed = speed
        if self._fan_mode != self.FanMode.MANUAL:
            await self.set_fan_mode(self.FanMode.MANUAL)
        pwm = hex(int(self._speed))
        if self._speed != pwm:
            self._speed = pwm
            result = await self.ipmi.execute(f"raw 0x30 0x30 0x02 0xff {self._speed}")
            if result.stdout != "\n":
                raise Exception
