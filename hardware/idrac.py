import logging

logger = logging.getLogger(__name__)
from enum import IntEnum
import subprocess
import shlex
import requests
import json
from requests.packages import urllib3

try:
    import mysecret
except:
    logger.info("mysecret was not loaded")
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# https://www.dell.com/support/manuals/en-us/idrac9-lifecycle-controller-v6.x-series/idrac9_6.xx_racadm_pub/introduction
# https://dl.dell.com/content/manual35024470-integrated-dell-remote-access-controller-9-racadm-cli-guide.pdf?language=en-us
# https://www.dell.com/support/manuals/en-us/idrac9-lifecycle-controller-v6.x-series/idrac9_6.xx_racadm_ar_guide/notes-cautions-and-warnings
# https://dl.dell.com/content/manual36782628-integrated-dell-remote-access-controller-9-attribute-registry.pdf?language=en-us
# https://www.dell.com/support/manuals/en-us/idrac9-lifecycle-controller-v6.x-series/idrac9_6.xx_ug/notes-cautions-and-warnings
# https://dl.dell.com/content/manual38875502-integrated-dell-remote-access-controller-9-user-s-guide.pdf?language=en-us


class Redfish:
    class Fan_Offset(IntEnum):
        OFF = 0
        LOW = 1
        MEDIUM = 2
        HIGH = 3
        MAX = 4

    def __init__(self, address, username="root", password="calvin"):
        self.address = address
        self.username = username
        self.password = password
        self.base_path = f"https://{self.address}/redfish/v1/"
        self._temp = 0
        self._pwm = 0

    def close(self):
        pass

    def get(self, path):
        response = requests.get(
            f"{self.base_path}{path}",
            verify=False,
            auth=(self.username, self.password),
        )
        return json.loads(response.content)

    def set(self, path, payload):
        headers = {"content-type": "application/json"}
        response = requests.patch(
            f"{self.base_path}{path}",
            data=json.dumps(payload),
            headers=headers,
            verify=False,
            auth=(self.username, self.password),
        )
        return json.loads(response.content)

    def get_fan_offset(self):
        offset_str = self.get("Managers/System.Embedded.1/Attributes?$select=ThermalSettings.*")["Attributes"][
            "ThermalSettings.1.FanSpeedOffset"
        ]
        offsets = {
            "Off": self.Fan_Offset.OFF,
            "Low": self.Fan_Offset.LOW,
            "Medium": self.Fan_Offset.MEDIUM,
            "High": self.Fan_Offset.HIGH,
            "Max": self.Fan_Offset.MAX,
        }
        offset = offsets[offset_str]
        return offset

    def set_fan_offset(self, offset):
        if isinstance(offset, str) is True:
            offsets = {
                "Off": self.Fan_Offset.OFF,
                "Low": self.Fan_Offset.LOW,
                "Medium": self.Fan_Offset.MEDIUM,
                "High": self.Fan_Offset.HIGH,
                "Max": self.Fan_Offset.MAX,
            }
            offset = offsets[offset]
        offsets = {
            self.Fan_Offset.OFF: "Off",
            self.Fan_Offset.LOW: "Low",
            self.Fan_Offset.MEDIUM: "Medium",
            self.Fan_Offset.HIGH: "High",
            self.Fan_Offset.MAX: "Max",
        }
        output = self.set(
            "Managers/System.Embedded.1/Attributes",
            {"Attributes": {"ThermalSettings.1.FanSpeedOffset": offsets[offset]}},
        )
        output = json.dumps(output)
        output.index("The request completed successfully.")
        output.index("The operation successfully completed.")

    def get_cpu_temp(self):
        return int(self.get("Chassis/System.Embedded.1/Sensors/CPU1Temp")["Reading"])

    def get_pwm(self):
        offset = self.get_fan_offset()
        pwms = {
            self.Fan_Offset.OFF: 0,
            self.Fan_Offset.LOW: 25,
            self.Fan_Offset.MEDIUM: 50,
            self.Fan_Offset.HIGH: 75,
            self.Fan_Offset.MAX: 100,
        }
        self._pwm = pwms[offset]
        return self._pwm

    def set_pwm(self, pwm):
        logger.info(f"pwm changed {pwm}")
        self._pwm = pwm
        if pwm < 25:
            self.set_pwm_offset(self.Fan_Offset.OFF)
        elif pwm < 50:
            self.set_pwm_offset(self.Fan_Offset.LOW)
        elif pwm < 75:
            self.set_pwm_offset(self.Fan_Offset.MEDIUM)
        elif pwm < 100:
            self.set_pwm_offset(self.Fan_Offset.HIGH)
        else:
            self.set_pwm_offset(self.Fan_Offset.MAX)


class Ipmi:
    class FanMode(IntEnum):
        MANUAL = 0
        IDRAC = 1

    def __init__(self, address, username="root", password="calvin"):
        self.address = address
        self.username = username
        self.password = password
        self.base_cmd = f"ipmitool -I lanplus -H {self.address} -U {self.username} -P {self.password}"
        self._temp = 0
        self._pwm = 0
        self.set_fan_mode(self.FanMode.MANUAL)

    def close(self):
        self.set_fan_mode(self.FanMode.IDRAC)

    def run_cmd(self, cmd):
        full_cmd = f"{self.base_cmd} {cmd}"
        value = subprocess.run(shlex.split(full_cmd), capture_output=True, timeout=5)
        value = value.stdout.decode("utf-8")
        return value

    def set_fan_mode(self, mode):
        self.run_cmd(f"raw 0x30 0x30 0x01 0x0{int(mode)}")

    def get_cpu_temp(self):
        return int(self.run_cmd('-c sdr get "Temp"').split(",")[1])

    def set_pwm(self, pwm):
        pwm_set = hex(int(pwm))
        self.run_cmd(f"raw 0x30 0x30 0x02 0xff {pwm_set}")


if __name__ == "__main__":
    i = Ipmi("10.1.1.204", password=mysecret.password)
    logger.info(i.get_cpu_temp())
    i.set_pwm(50)
    # i.close()
    # r = Redfish("10.1.7.180", password=mysecret.password)
    # logger.info(r.cpu_temp)

    # r.fan_offset = r.Fan_Offset.OFF
    # logger.info(r.fan_offset)

    # offsets = [r.Fan_Offset.OFF, r.Fan_Offset.LOW, r.Fan_Offset.MEDIUM, r.Fan_Offset.HIGH, r.Fan_Offset.MAX]
    # for o in offsets:
    #     r.fan_offset = o
    #     logger.info(r.fan_offset)
    # r.fan_offset = r.Fan_Offset.OFF
