from . import *

logger = logging.getLogger(__name__)
import subprocess
import shlex
import re
import numpy as np


class Gpu(Device):
    def __init__(self, address, password, username="root"):
        super().__init__(address=address, password=password, username=username)
        self.base_cmd = f"sshpass -p {self._password} ssh -o StrictHostKeychecking=no {self._username}@{self._address}"
        self._full_cmd = ""

    def ssh_cmd(self, command):
        self._full_cmd = f"{self.base_cmd} {command}"
        value = subprocess.run(shlex.split(self._full_cmd, posix=False), capture_output=True, timeout=5)
        value = value.stdout.decode("utf-8")
        return value


class Nvidia(Gpu):
    def get_temp(self):
        try:
            output = self.ssh_cmd(f"nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader")
            temp_list = output.strip().split(",")
            temp_list = list(map(int, output))
            temp = int(np.mean(temp_list))
            return temp
        except Exception as e:
            logger.info(f"{self._address} failed to get gpu temperature:")
            logger.info(f"cmd = {self._full_cmd}")
            logger.info(f"output = {output}")
            raise e


def test():
    n = Nvidia(address="10.1.5.2", password=my_secret_password, username="root")
    print(n.get_temp())


if __name__ == "__main__":
    test()
