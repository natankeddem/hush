import logging

logger = logging.getLogger(__name__)
from typing import Any, Dict, List, Optional
import re
import numpy as np
from . import Device


class Smart(Device):
    def __init__(self, host: str, drives: Optional[List[str]] = None) -> None:
        super().__init__(host)
        self._drives = drives
        self.get_os_credentials()

    async def get_drive_list(self):
        drive_paths = []
        try:
            result = await self.ssh.shell("fdisk -l")
            drive_paths = re.findall(r"Disk (\/dev\/sd[a-z]+|\/dev\/nvme[0-9]+n[0-9]+)", result.stdout)
        except Exception as e:
            logger.info(f"{self} failed to get drive list:")
            logger.info(f"result = {result}")
            raise e
        return drive_paths

    async def get_drive_temp(self, drive_path):
        try:
            result = await self.ssh.shell(f'smartctl -x {drive_path} | grep -E "Temperature|temperature"')
            for line in result.stdout_lines:
                temp = re.search(r"^(?:Current(?:\sDrive)?\s)?Temperature:\s*(\d+)", line)
                if temp is not None and temp.lastindex == 1:
                    return float(temp.group(1))
            logger.info(f"{self.hostname} failed to get drive temperature {drive_path}:")
            logger.info(f"result = {result}")
            return None
        except Exception as e:
            logger.info(f"{self.hostname} failed to get drive temperature {drive_path}:")
            logger.info(f"result = {result}")
            raise e

    async def get_temp(self):
        try:
            drive_temps = list()
            if self._drives is None or self._drives == []:
                self._drives = await self.get_drive_list()
            for drive_path in self._drives:
                temp = await self.get_drive_temp(drive_path=drive_path)
                if temp is not None:
                    drive_temps.append(float(temp))
            self._temp = int(np.mean(drive_temps))
            return self._temp
        except Exception as e:
            logger.info(f"drive_paths = {self._drives}")
            logger.info(f"drive_temps = {drive_temps}")
            raise e
