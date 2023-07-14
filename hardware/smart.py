import logging

logger = logging.getLogger(__name__)
from enum import IntEnum
import subprocess
import shlex
import re
from requests.packages import urllib3
import numpy as np

try:
    import mysecret
except:
    logger.info("mysecret was not loaded")
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class Smart:
    def __init__(self, address, username="root", password=""):
        self.address = address
        self.username = username
        self.password = password
        self.base_cmd = f"sshpass -p {self.password} ssh -o StrictHostKeychecking=no {self.username}@{self.address}"
        self._temp = 0

    def close(self):
        pass

    def ssh_cmd(self, command):
        full_cmd = f"{self.base_cmd} {command}"
        value = subprocess.run(shlex.split(full_cmd), capture_output=True, timeout=5)
        value = value.stdout.decode("utf-8")
        return value

    def get_drive_list(self):
        drive_paths = list()
        drive_lines = self.ssh_cmd("fdisk -l").splitlines()
        for line in drive_lines:
            drive_path = re.search("^Disk (\/dev\/sd[a-z]+|\/dev\/nvm[0-9]+n[0-9]+)", line)
            if drive_path is not None:
                drive_paths.append(drive_path.group(1))
        return drive_paths

    def get_drive_temp(self, drive_path):
        status_lines = self.ssh_cmd(f"smartctl -l scttemp {drive_path}").splitlines()
        for line in status_lines:
            temp = re.search("^Current Temperature:\s+(\d+)", line)
            if temp is not None:
                return int(temp.group(1))

    def get_drives_temps(self):
        drive_temps = list()
        drive_paths = self.get_drive_list()
        for drive_path in drive_paths:
            temp = self.get_drive_temp(drive_path=drive_path)
            if temp is not None:
                drive_temps.append(temp)
        return int(np.mean(drive_temps))


if __name__ == "__main__":
    s = Smart(address="10.1.5.2", username="root", password=mysecret.password)
    print(s.get_drives_temps())
