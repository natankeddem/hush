from . import *

logger = logging.getLogger(__name__)
from enum import IntEnum
import subprocess
import shlex
import numpy as np
import re


class X9(Device):
    class Fan_Mode(IntEnum):
        STANDARD = 0
        FULL = 1
        OPTIMAL = 2
        HEAVYIO = 4

    def __init__(self, address, username="ADMIN", password="ADMIN"):
        super().__init__(address=address, password=password, username=username)
        self.base_cmd = f"ipmitool -I lanplus -H {self._address} -U {self._username} -P {self._password}"
        self._fan_mode = None

    def close(self):
        self.set_fan_mode(self.Fan_Mode.STANDARD)

    def run_cmd(self, cmd):
        full_cmd = f"{self.base_cmd} {cmd}"
        value = subprocess.run(shlex.split(full_cmd), capture_output=True, timeout=5)
        if value.returncode != 0:
            logger.error(f"{self._address} failed to run_cmd {full_cmd}")
            raise Exception
        value = value.stdout.decode("utf-8")
        return value

    def get_temp(self, core=None):
        cpu_temps = list()
        try:
            sensors = ["CPU Temp", "CPU1 Temp", "CPU2 Temp"]
            for sensor in sensors:
                output = self.run_cmd(f'-c sdr get "{sensor}"')
                data = output.split(",")
                if data[0] == sensor and data[1] != "":
                    cpu_temps.append(float(data[1]))
            if core is None:
                self._temp = int(np.mean(cpu_temps))
            else:
                self._temp = cpu_temps[core]
            return self._temp
        except Exception as e:
            logger.error(f"{self._address} failed to get cpu temperature from: {output}")
            raise e

    def get_fan_mode(self):
        mode = self.Fan_Mode(int(self.run_cmd("raw 0x30 0x45 0")))
        self._fan_mode = mode
        return mode

    def set_fan_mode(self, mode):
        self._fan_mode = mode
        self.run_cmd(f"raw 0x30 0x45 0x01 {self._fan_mode.value}")

    def set_speed(self, speed):
        self._speed = speed
        if self._fan_mode != self.Fan_Mode.FULL:
            self.set_fan_mode(self.Fan_Mode.FULL)
        pwm = hex(int(self._speed / (100 / 255)))
        self.run_cmd(f"raw 0x30 0x91 0x5A 0x03 0x10 {pwm}")
        self.run_cmd(f"raw 0x30 0x91 0x5A 0x03 0x11 {pwm}")


class X10(X9):
    def set_speed(self, speed):
        self._speed = speed
        if self._fan_mode != self.Fan_Mode.FULL:
            self.set_fan_mode(self.Fan_Mode.FULL)
        pwm = hex(int(self._speed / (100 / 255)))
        self.run_cmd(f"raw 0x30 0x70 0x66 0x01 0x10 {pwm}")
        self.run_cmd(f"raw 0x30 0x70 0x66 0x01 0x11 {pwm}")


class X11(X10):
    pass


def test():
    x = X9("10.1.7.226")
    print(x.get_temp())
    x.set_speed(10)
    x.close()


if __name__ == "__main__":
    test()
