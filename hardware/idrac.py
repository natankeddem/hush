from . import *

logger = logging.getLogger(__name__)
from enum import IntEnum
import subprocess
import shlex
import requests
import json
import re
from requests.packages import urllib3
import numpy as np

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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

    def __init__(self, address, username="root", password="calvin"):
        super().__init__(address=address, password=password, username=username)
        self.base_path = f"https://{self._address}/redfish/v1/"

    def close(self):
        pass

    def redfish_cmd(self, path, payload=None):
        if payload is None:
            response = requests.get(
                f"{self.base_path}{path}",
                verify=False,
                auth=(self._username, self._password),
            )
        else:
            json_payload = json.dumps(payload)
            headers = {"content-type": "application/json"}
            response = requests.patch(
                f"{self.base_path}{path}",
                data=json_payload,
                headers=headers,
                verify=False,
                auth=(self._username, self._password),
            )
        return json.loads(response.content)

    def get_temp(self, core=None):
        cpu_temps = list()
        try:
            sensors = str(self.redfish_cmd(path="Chassis/System.Embedded.1/Sensors"))
            sensor_paths = re.findall(r"Chassis\/System.Embedded.1\/Sensors\/CPU\dTemp", sensors)
            for sensor_path in sensor_paths:
                sensor_data = self.redfish_cmd(path=f"{sensor_path}")
                cpu_temps.append(float(sensor_data["Reading"]))
        except Exception as e:
            logger.error(f"{self._address} failed to get cpu temperature from: {sensor_data}")
            raise e
        if core is None:
            self._temp = int(np.mean(cpu_temps))
        else:
            self._temp = cpu_temps[core]
        return self._temp

    def set_speed(self, speed):
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
            output = self.redfish_cmd(
                path="Managers/System.Embedded.1/Attributes",
                payload={"Attributes": {"ThermalSettings.1.FanSpeedOffset": self._speed}},
            )
            output = json.dumps(output)
            try:
                output.index("The request completed successfully.")
                output.index("The operation successfully completed.")
            except Exception as e:
                logger.error(f"{self._address} failed to set offset; cmd response: {output}")
                raise e


class Ipmi(Device):
    class FanMode(IntEnum):
        MANUAL = 0
        IDRAC = 1

    def __init__(self, address, username="root", password="calvin"):
        super().__init__(address=address, password=password, username=username)
        self.base_cmd = f"ipmitool -I lanplus -H {self._address} -U {self._username} -P {self._password}"
        self._fan_mode = None

    def close(self):
        self.set_fan_mode(self.FanMode.IDRAC)

    def run_cmd(self, cmd):
        full_cmd = f"{self.base_cmd} {cmd}"
        value = subprocess.run(shlex.split(full_cmd), capture_output=True, timeout=10)
        if value.returncode != 0:
            logger.error(f"{self._address} failed to run_cmd {full_cmd}")
            raise Exception
        value = value.stdout.decode("utf-8")
        return value

    def set_fan_mode(self, mode):
        if self.run_cmd(f"raw 0x30 0x30 0x01 0x0{int(mode)}") != "\n":
            raise Exception
        else:
            self._fan_mode = mode

    def get_temp(self, core=None):
        cpu_temps = list()
        try:
            output = self.run_cmd("-c sdr")
            data_lines = output.splitlines()
            for data in data_lines:
                data = data.split(",")
                if data[0] == "Temp" and data[1] != "":
                    cpu_temps.append(float(data[1]))
            if core is None:
                self._temp = int(np.mean(cpu_temps))
            else:
                self._temp = cpu_temps[core]
            return self._temp
        except Exception as e:
            logger.error(f"{self._address} failed to get cpu temperature from: {output}")
            raise e

    def set_speed(self, speed):
        self._speed = speed
        if self._fan_mode != self.FanMode.MANUAL:
            self.set_fan_mode(self.FanMode.MANUAL)
        pwm = hex(int(self._speed))
        if self._speed != pwm:
            self._speed = pwm
            if self.run_cmd(f"raw 0x30 0x30 0x02 0xff {self._speed}") != "\n":
                raise Exception


def test():
    # i = Ipmi("10.1.1.204", password=my_secret_password)
    # print(i.get_temp())
    # i.set_speed(20)
    # i.close()

    r = Redfish("10.1.7.180", password=my_secret_password)
    print(r.get_temp())
    r.set_speed(r.Fan_Offset.OFF)
    r.set_speed("Low")
    r.set_speed(74)
    r.close()


if __name__ == "__main__":
    test()
