from . import *

logger = logging.getLogger(__name__)
import subprocess
import shlex
import re
import numpy as np


class Smart(Device):
    def __init__(self, address, password, username="root"):
        super().__init__(address=address, password=password, username=username)
        self.base_cmd = f"sshpass -p {self._password} ssh -o StrictHostKeychecking=no {self._username}@{self._address}"
        self._full_cmd = ""

    def ssh_cmd(self, command):
        self._full_cmd = f"{self.base_cmd} {command}"
        value = subprocess.run(shlex.split(self._full_cmd, posix=False), capture_output=True, timeout=5)
        value = value.stdout.decode("utf-8")
        return value

    def get_drive_list(self):
        drive_paths = list()
        try:
            output = self.ssh_cmd("fdisk -l")
            drive_paths = re.findall(r"Disk (\/dev\/sd[a-z]+|\/dev\/nvm[0-9]+n[0-9]+)", output)
        except Exception as e:
            logger.info(f"{self._address} failed to get drive list:")
            logger.info(f"cmd = {self._full_cmd}")
            logger.info(f"output = {output}")
            raise e
        return drive_paths

    def get_drive_temp(self, drive_path):
        try:
            output = self.ssh_cmd(f'smartctl -x {drive_path} | grep -E "Temp|Cel|Cur|temp|cel|cur"')
            temp = re.search(r"Current\s*[^T]*Temperature:\s*(\d+)", output)
            if temp is not None and temp.lastindex == 1:
                return float(temp.group(1))
            else:
                logger.info(f"{self._address} failed to get drive temperature {drive_path}:")
                logger.info(f"cmd = {self._full_cmd}")
                logger.info(f"output = {output}")
        except Exception as e:
            logger.info(f"{self._address} failed to get drive temperature {drive_path}:")
            logger.info(f"cmd = {self._full_cmd}")
            logger.info(f"output = {output}")
            raise e

    def get_temp(self):
        try:
            drive_temps = list()
            drive_paths = self.get_drive_list()
            for drive_path in drive_paths:
                temp = self.get_drive_temp(drive_path=drive_path)
                if temp is not None:
                    drive_temps.append(float(temp))
            self._temp = int(np.mean(drive_temps))
            return self._temp
        except Exception as e:
            logger.info(f"drive_paths = {drive_paths}")
            logger.info(f"drive_temps = {drive_temps}")
            raise e


def test():
    s = Smart(address="10.1.5.2", password=my_secret_password, username="root")
    print(s.get_temp())


if __name__ == "__main__":
    test()
