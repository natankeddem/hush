import logging

logger = logging.getLogger(__name__)
import numpy as np
from . import Device


class Gpu(Device):
    def __init__(self, host: str) -> None:
        super().__init__(host)
        self.get_os_credentials()

    async def get_temp(self):
        try:
            result = await self.ssh.shell(f"nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader")
            temperatures = []
            for temperature in result.stdout_lines:
                temperatures.append(float(temperature.strip()))
            temperature = int(np.max(temperatures))
            return temperature
        except Exception as e:
            logger.info(f"{self.hostname} failed to get gpu temperature:")
            logger.info(f"result = {result}")
            raise e

    async def set_speed(self, speed):
        result = await self.ssh.execute(f'export DISPLAY=:0 && nvidia-settings -c $DISPLAY  -a "GPUFanControlState=1" -a "GPUTargetFanSpeed={speed}"')
        if result.stdout.count("assigned value") != 2:
            raise SystemError

    async def close(self):
        await self.ssh.execute('export DISPLAY=:0 && nvidia-settings -c $DISPLAY  -a "GPUFanControlState=0"')
