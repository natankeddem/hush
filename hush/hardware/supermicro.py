import logging

logger = logging.getLogger(__name__)
from typing import Optional
from enum import IntEnum
import numpy as np
from . import Device


class X9(Device):
    class FanMode(IntEnum):
        STANDARD = 0
        FULL = 1
        OPTIMAL = 2
        HEAVYIO = 4

    def __init__(self, host: str) -> None:
        super().__init__(host)
        self.get_oob_credentials()
        self._fan_mode: Optional[X9.FanMode] = None
        self.fru: Optional[dict] = None

    async def close(self):
        await self.set_fan_mode(self.FanMode.STANDARD)

    async def get_temp(self, core=None):
        cpu_temps = list()
        try:
            result = await self.ipmi.execute("-c sdr")
            sensors = ["CPU Temp", "CPU1 Temp", "CPU2 Temp"]
            for sensor in sensors:
                for line in result.stdout_lines:
                    if sensor in line:
                        data = line.split(",")
                        if data[0] == sensor and data[1] != "":
                            cpu_temps.append(float(data[1]))
            if core is None:
                self._temp = int(np.mean(cpu_temps))
            else:
                self._temp = int(cpu_temps[core])
            return self._temp
        except Exception as e:
            logger.error(f"{self.hostname} failed to get cpu temperature from: {result}")
            raise e

    async def get_fan_mode(self) -> FanMode:
        result = await self.ipmi.execute("raw 0x30 0x45 0")
        self._fan_mode = self.FanMode(int(result.stdout))
        return self._fan_mode

    async def set_fan_mode(self, mode: FanMode) -> None:
        if self._fan_mode != mode:
            await self.ipmi.execute(f"raw 0x30 0x45 0x01 {mode.value}")
            self._fan_mode = mode

    async def set_speed(self, speed):
        self._speed = speed
        await self.set_fan_mode(self.FanMode.FULL)
        if speed != self._speed:
            pwm = hex(int(speed / (100 / 255)))
            await self.ipmi.execute(f"raw 0x30 0x91 0x5A 0x03 0x10 {pwm}")
            await self.ipmi.execute(f"raw 0x30 0x91 0x5A 0x03 0x11 {pwm}")
            self._speed = speed

    async def board_part_number(self) -> str:
        if self.fru is None:
            result = await self.ipmi.execute("fru")
            self.fru = {}
            for line in result.stdout_lines:
                data = line.split(":")
                if len(data) > 1:
                    self.fru.update({data[0].strip(): data[1].strip()})
            logger.info(f"fru = {self.fru}")
        return self.fru.get("Board Part Number", "")


class X10(X9):
    async def set_speed(self, speed):
        await self.set_fan_mode(self.FanMode.FULL)
        if speed != self._speed:
            pwm = hex(int(speed / (100 / 255)))
            board_part_number = await self.board_part_number()
            if "X10DRG" in board_part_number:
                zones = ["00", "01", "02", "03"]
            else:
                zones = ["00", "01"]
            for zone in zones:
                await self.ipmi.execute(f"raw 0x30 0x70 0x66 0x01 0x{zone} {pwm}")
            self._speed = speed


class X11(X10):
    pass


class Gpu(X9):
    async def get_temp(self):
        gpu_temps = list()
        try:
            result = await self.ipmi.execute("-c sdr")
            sensors = ["GPU Temp", "GPU1 Temp", "GPU2 Temp", "GPU3 Temp", "GPU4 Temp", "GPU5 Temp", "GPU6 Temp"]
            for sensor in sensors:
                for line in result.stdout_lines:
                    if sensor in line:
                        data = line.split(",")
                        if data[0] == sensor and data[1] != "":
                            gpu_temps.append(float(data[1]))
            self._temp = int(np.mean(gpu_temps))
            return self._temp
        except Exception as e:
            logger.error(f"{self.hostname} failed to get gpu temperature from: {result}")
            raise e
