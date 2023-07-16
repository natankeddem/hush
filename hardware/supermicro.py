import logging

logger = logging.getLogger(__name__)
from enum import IntEnum
import subprocess
import shlex
import numpy as np
import re


class X9:
    class Fan_Mode(IntEnum):
        STANDARD = 0
        FULL = 1
        OPTIMAL = 2
        HEAVYIO = 4

    def __init__(self, address, username="ADMIN", password="ADMIN"):
        self.address = address
        self.username = username
        self.password = password
        self.base_cmd = f"ipmitool -I lanplus -H {self.address} -U {self.username} -P {self.password}"
        self._fan_mode = None

    def run_cmd(self, cmd):
        full_cmd = f"{self.base_cmd} {cmd}"
        value = subprocess.run(shlex.split(full_cmd), capture_output=True, timeout=5)
        if value.returncode != 0:
            raise Exception
        value = value.stdout.decode("utf-8")
        return value

    def close(self):
        self.set_fan_mode(self.Fan_Mode.STANDARD)

    def get_system_names(self):
        fru = self.run_cmd("fru").strip().split("\n")
        names = dict()
        for name in fru:
            name = name.split(":")
            names.update({name[0].strip(): name[1].strip()})
        return names

    def get_cpu_temp(self, core=None):
        cpu_temps = list()
        try:
            sensors = ["CPU Temp", "CPU1 Temp", "CPU2 Temp"]
            for sensor in sensors:
                output = self.run_cmd(f'-c sdr get "{sensor}"')
                data = output.split(",")
                if data[0] == sensor and data[1] != "":
                    cpu_temps.append(int(data[1]))
            if core is None:
                return int(np.mean(cpu_temps))
            else:
                return cpu_temps[core]
        except Exception as e:
            logger.error(f"Failed to get cpu temperature from: {output}")
            raise e

    def get_fan_mode(self):
        mode = self.Fan_Mode(int(self.run_cmd("raw 0x30 0x45 0")))
        self._fan_mode = mode
        return mode

    def set_fan_mode(self, mode):
        self._fan_mode = mode
        self.run_cmd(f"raw 0x30 0x45 0x01 {mode.value}")

    def set_pwm(self, pwm):
        if self._fan_mode != self.Fan_Mode.FULL:
            self.set_fan_mode(self.Fan_Mode.FULL)
        self._pwm = pwm
        pwm_set = hex(int(pwm / (100 / 255)))
        self.run_cmd(f"raw 0x30 0x91 0x5A 0x03 0x10 {pwm_set}")
        self.run_cmd(f"raw 0x30 0x91 0x5A 0x03 0x11 {pwm_set}")


class X10(X9):
    def set_pwm(self, pwm):
        if self._fan_mode != self.Fan_Mode.FULL:
            self.set_fan_mode(self.Fan_Mode.FULL)
        self._pwm = pwm
        pwm_set = hex(int(pwm / (100 / 255)))
        self.run_cmd(f"raw 0x30 0x70 0x66 0x01 0x10 {pwm_set}")
        self.run_cmd(f"raw 0x30 0x70 0x66 0x01 0x11 {pwm_set}")


class X11(X10):
    pass


if __name__ == "__main__":
    x = X9("10.1.7.226")
    print(x.get_cpu_temp())
    x.set_pwm(20)
