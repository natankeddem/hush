import logging

logger = logging.getLogger(__name__)
from enum import IntEnum
import subprocess
import shlex
import requests
import json
from requests.packages import urllib3
import numpy as np

try:
    import mysecret
except:
    logger.info("mysecret was not loaded")
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class iLO4:
    def __init__(self, address, username="Administrator", password=""):
        self.address = address
        self.username = username
        self.password = password
        self.redfish_base_path = f"https://{self.address}/redfish/v1/"
        self.base_cmd = f"sshpass -p {self.password} ssh -o StrictHostKeychecking=no {self.username}@{self.address} -o PubKeyAcceptedKeyTypes=+ssh-rsa -o HostKeyAlgorithms=+ssh-dss -o KexAlgorithms=+diffie-hellman-group14-sha1"
        self._temp = 0
        self._pwm = 0
        self.get_fan_count()

    def close(self):
        for fan in range(self._fan_count):
            self.ssh_cmd(f"fan p {fan} unlock")

    def redfish_get(self, path):
        response = requests.get(
            f"{self.redfish_base_path}{path}",
            verify=False,
            auth=(self.username, self.password),
        )
        return json.loads(response.content)

    def ssh_cmd(self, command):
        full_cmd = f"{self.base_cmd} {command}"
        value = subprocess.run(shlex.split(full_cmd), capture_output=True, timeout=5)
        value = value.stdout.decode("utf-8")
        return value

    def get_fan_count(self):
        fans = self.redfish_get("chassis/1/Thermal")["Fans"]
        self._fan_count = len(fans)
        return self._fan_count

    def get_cpu_temp(self, core=None):
        cpu_temps = list()
        temperatures = self.redfish_get("chassis/1/Thermal")["Temperatures"]
        for t in temperatures:
            if t["Name"].find("CPU") != -1:
                cpu_temps.append(int(t["CurrentReading"]))
        if core is None:
            return int(np.mean(cpu_temps))
        else:
            return cpu_temps[core]

    def set_pwm(self, pwm):
        pwm_set = (pwm / 100) * 255
        for fan in range(self._fan_count):
            self.ssh_cmd(f"fan p {fan} lock {pwm_set}")


if __name__ == "__main__":
    s = iLO4(address="10.1.4.50", username="Administrator", password=mysecret.password)
    logger.info(s.get_cpu_temp())
    s.set_pwm(35)
